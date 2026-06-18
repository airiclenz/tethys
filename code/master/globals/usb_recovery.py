# =============================================================================
# USB camera recovery — re-enumerate a webcam that has fallen off the bus.
#
# The verified USB webcam (Anker PowerConf C200) occasionally throws a burst of
# -71 (EPROTO) UVC errors mid-session and the kernel disconnects it. Once the
# device is gone from the bus it cannot be revived by `usbreset` (no device node
# left to ioctl) nor by restarting the camera *process* — it needs the USB host
# controller re-enumerated. On the Pi 4 the external ports hang off the VL805
# xHCI controller on the PCIe bus; unbinding and rebinding its xhci_hcd driver
# re-initialises the controller and brings a crashed device back.
#
# Privilege: the sysfs writes here are root-only. This module is only ever run by
# a root process (tethys-api / tethys-watchdog); the unprivileged camera service
# never performs the reset — it only surfaces the need for one to the UI, which
# asks the root API to do it.
#
# Safety: a controller rebind briefly drops EVERY device on that controller. That
# is safe on this box (rootfs is on the SD card, the camera is the only thing on
# USB), and _root_on_usb() refuses to run if that ever stops being true.
#
# Stdlib only, so it imports cleanly under any service's venv and is unit-testable
# against a fake sysfs/proc tree: the filesystem roots below are module-level so a
# test can point them at a tmp dir.
# =============================================================================

import contextlib
import errno
import fcntl
import glob
import logging
import os
import subprocess
import time


log = logging.getLogger("tethys.usb_recovery")

# The one verified camera (Anker PowerConf C200). Recovery keys off the USB
# VID:PID, not a /dev/video* node, because the whole point is that the node has
# vanished — only the bus-level identity survives a re-enumeration question.
CAMERA_VENDOR_ID = "291a"
CAMERA_PRODUCT_ID = "3369"

# Filesystem roots, module-level so tests can redirect them at a fixture tree.
USB_DEVICES_GLOB = "/sys/bus/usb/devices/*"
XHCI_DRIVER_DIR = "/sys/bus/pci/drivers/xhci_hcd"
PROC_MOUNTS = "/proc/mounts"
SYS_BLOCK = "/sys/block"

# Cross-process lock file (tmpfs, root-writable). Serialises the destructive USB
# re-enumeration across its two callers — see _recovery_lock(). Module-level so a
# test can point it at a tmp dir.
RECOVERY_LOCK_FILE = "/run/tethys-usb-recovery.lock"

SETTLE_SECONDS = 2          # gap between unbind and rebind
WAIT_SECONDS = 12           # how long to wait for the device to re-enumerate
POLL_SECONDS = 0.5          # bus re-check cadence while waiting
RESTART_CAMERA = True       # restart tethys-camera.service after a reset
SYSTEMCTL = "/usr/bin/systemctl"
CAMERA_SERVICE = "tethys-camera.service"


def _read(path):
    '''Read and strip a sysfs/proc file; "" on any error (absent node, race,
    permission) so callers can treat every probe uniformly.'''
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return ""


# =============================================================================
def camera_present(vendor_id=CAMERA_VENDOR_ID, product_id=CAMERA_PRODUCT_ID):
    '''True if the camera's USB VID:PID is currently enumerated on the bus. This
    is the health signal both triggers key off — a missing capture node could be
    a transient probe failure, but a missing VID:PID means the device is genuinely
    off the bus.'''
    for device in glob.glob(USB_DEVICES_GLOB):
        if (_read(os.path.join(device, "idVendor")).lower() == vendor_id.lower()
                and _read(os.path.join(device, "idProduct")).lower()
                == product_id.lower()):
            return True
    return False


# =============================================================================
def xhci_pci_devices():
    '''The xHCI USB host controllers' PCI addresses (e.g. "0000:01:00.0"),
    discovered from the driver dir so nothing is hard-coded. A bound controller
    appears as a symlink named by its PCI address; the driver's own attribute
    files (bind/unbind/uevent/...) carry no ":" and are skipped.'''
    addresses = []
    for entry in sorted(glob.glob(os.path.join(XHCI_DRIVER_DIR, "*"))):
        name = os.path.basename(entry)
        if ":" in name and os.path.islink(entry):
            addresses.append(name)
    return addresses


# =============================================================================
def _base_block_name(name):
    '''Strip a partition suffix to the parent block device: "mmcblk0p2"->"mmcblk0",
    "nvme0n1p1"->"nvme0n1", "sda2"->"sda". mmc/nvme use a "p<N>" suffix; sd/vd put
    the partition number directly on the name.'''
    if name.startswith("mmcblk") or name.startswith("nvme"):
        index = name.rfind("p")
        if index > 0 and name[index + 1:].isdigit():
            return name[:index]
        return name
    return name.rstrip("0123456789")


def _root_block_devices():
    '''Base block device names backing "/" and the boot partition (e.g. "mmcblk0").
    Read from /proc/mounts so it reflects the running system, not fstab.'''
    targets = {"/", "/boot", "/boot/firmware"}
    devices = set()
    for line in _read(PROC_MOUNTS).splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        source, mount = parts[0], parts[1]
        if mount in targets and source.startswith("/dev/"):
            devices.add(_base_block_name(source[len("/dev/"):]))
    return devices


def _device_is_usb(block_name):
    '''True if a block device (e.g. "sda") traces through a USB controller — its
    /sys/block/<dev> realpath has a "usbN" segment. That is the signature of a USB
    SSD/stick; an SD card (mmcblk*) or NVMe drive resolves through an mmc/pcie path
    with no usb segment.'''
    real = os.path.realpath(os.path.join(SYS_BLOCK, block_name))
    return any(segment.startswith("usb") for segment in real.split("/"))


def _root_on_usb():
    '''True if "/" or the boot partition is backed by a USB block device — in which
    case re-enumerating the controller would yank the rootfs, so we must NOT reset.
    Verified false on this box (rootfs on the SD card); the guard exists so a future
    USB-boot setup can't be bricked by an auto-heal.'''
    for block_name in _root_block_devices():
        if block_name and _device_is_usb(block_name):
            return True
    return False


# =============================================================================
def _write_sysfs(path, value):
    '''Write a value to a sysfs attribute; True on success. A single failed
    unbind/bind is logged, not raised, so the recovery attempt continues.'''
    try:
        with open(path, "w") as handle:
            handle.write(value)
        return True
    except OSError as e:
        log.error("write %r to %s failed: %s", value, path, e)
        return False


def reenumerate_usb():
    '''Unbind then rebind every xHCI host controller, forcing a full USB
    re-enumeration. Returns True if at least one controller was cycled. The PCI
    addresses are captured before the loop because unbind removes the symlink.'''
    controllers = xhci_pci_devices()
    if not controllers:
        log.error("no xhci_hcd controllers found under %s", XHCI_DRIVER_DIR)
        return False

    cycled = False
    for address in controllers:
        log.info("re-enumerating USB controller %s", address)
        if not _write_sysfs(os.path.join(XHCI_DRIVER_DIR, "unbind"), address):
            continue
        time.sleep(SETTLE_SECONDS)
        # The rebind can race the PCI core re-probing the device itself; an
        # "already bound" failure here is benign (the controller is back either
        # way), so _write_sysfs logging it is enough.
        _write_sysfs(os.path.join(XHCI_DRIVER_DIR, "bind"), address)
        cycled = True
    return cycled


def _wait_for_camera():
    '''Poll the bus for up to WAIT_SECONDS; True as soon as the camera reappears.'''
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if camera_present():
            return True
        time.sleep(POLL_SECONDS)
    return camera_present()


def _restart_camera_service():
    '''Restart tethys-camera so its backend re-probes for the (possibly renamed)
    capture node and drops any cached device. Best-effort: a failure is logged,
    never raised — the camera may already be usable without it.'''
    try:
        result = subprocess.run([SYSTEMCTL, "restart", CAMERA_SERVICE], timeout=30)
        if result.returncode != 0:
            log.error("%s restart returned %s", CAMERA_SERVICE, result.returncode)
    except (OSError, subprocess.SubprocessError) as e:
        log.error("could not restart %s: %s", CAMERA_SERVICE, e)


# =============================================================================
@contextlib.contextmanager
def _recovery_lock():
    '''Cross-process mutex around the destructive USB re-enumeration. Both the
    watchdog auto-heal (in-process) and the API endpoint (a separate
    usb_recovery.py process) reach recover_camera(); without this guard a second
    caller could unbind/rebind the xHCI controller while the first is mid-cycle
    and leave the whole bus down — the recovery action killing USB. Non-blocking:
    yields True to the single holder, False to any caller that finds a recovery
    already in flight, so it no-ops instead of piling on a second reset.'''
    handle = open(RECOVERY_LOCK_FILE, "a")          # "a": create, never truncate
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            # EAGAIN/EWOULDBLOCK/EACCES is "already held" (the case we expect under
            # contention); anything else is a real lock failure we must not mask.
            if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                raise
            yield False
            return
        yield True
    finally:
        handle.close()                              # closing the fd releases flock


# =============================================================================
def recover_camera():
    '''Bring a dropped USB camera back without a physical replug. Returns a small
    status dict describing what happened. Safe to call when the camera is fine (it
    no-ops) and when it's genuinely unplugged (it resets once and reports that the
    device is still absent, so a caller can back off rather than loop). Serialised
    across processes by _recovery_lock(): a call made while another recovery is
    already in flight no-ops with action "busy".'''
    with _recovery_lock() as acquired:
        if not acquired:
            log.info("USB recovery already in flight; ignoring duplicate request")
            return {"recovered": False, "action": "busy"}

        if camera_present():
            log.info("camera already present; no recovery needed")
            return {"recovered": True, "action": "none"}

        if _root_on_usb():
            log.error("refusing USB reset: rootfs/boot is on a USB device")
            return {"recovered": False, "action": "aborted", "reason": "root-on-usb"}

        log.warning("camera not on the bus; re-enumerating USB to recover it")
        if not reenumerate_usb():
            return {"recovered": False, "action": "reset-failed"}

        recovered = _wait_for_camera()
        if RESTART_CAMERA:
            _restart_camera_service()

        if recovered:
            log.info("camera recovered after USB re-enumeration")
        else:
            log.error("camera still absent after USB re-enumeration "
                      "(unplugged, unpowered, or dead hardware?)")
        return {"recovered": recovered, "action": "reset"}


# =============================================================================
def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = recover_camera()
    # Non-zero exit when recovery was needed but failed, so a detached caller or a
    # manual run can tell. "Already present" and "recovered" are success.
    return 0 if result.get("recovered") else 1


if __name__ == "__main__":
    raise SystemExit(main())
