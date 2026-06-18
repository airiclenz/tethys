# Tests for the USB camera recovery helper. The module keeps its sysfs/proc roots
# in module-level constants exactly so these tests can point them at a tmp fixture
# tree and exercise the detection + safety logic with no real hardware — the same
# "inject the seam" approach camera/tests uses with FakeSnapshotBackend. The
# destructive parts (reenumerate_usb / recover_camera) are covered by monkeypatching
# the module's own functions, so no sysfs is ever written.

import os

import pytest

from globals import usb_recovery


@pytest.fixture(autouse=True)
def _isolate_recovery_lock(monkeypatch, tmp_path):
    '''recover_camera() takes a cross-process flock on RECOVERY_LOCK_FILE (default
    /run/tethys-usb-recovery.lock); point it at a tmp file so the destructive-path
    tests never touch a real system path and don't need to run as root.'''
    monkeypatch.setattr(
        usb_recovery, "RECOVERY_LOCK_FILE", str(tmp_path / "usb-recovery.lock"))


# -- fixtures helpers ---------------------------------------------------------
def _make_usb_device(parent, name, vendor, product):
    '''A fake /sys/bus/usb/devices/<name> with idVendor/idProduct (trailing
    newlines, as the kernel writes them, so we also cover _read's strip()).'''
    device = parent / name
    device.mkdir()
    (device / "idVendor").write_text(vendor + "\n")
    (device / "idProduct").write_text(product + "\n")
    return device


# -- camera_present -----------------------------------------------------------
def test_camera_present_true(monkeypatch, tmp_path):
    usb = tmp_path / "usb"
    usb.mkdir()
    _make_usb_device(usb, "1-1", "2109", "3431")            # a hub
    _make_usb_device(usb, "1-1.1", "291a", "3369")          # the C200
    monkeypatch.setattr(usb_recovery, "USB_DEVICES_GLOB", str(usb / "*"))

    assert usb_recovery.camera_present() is True


def test_camera_present_false_when_only_other_devices(monkeypatch, tmp_path):
    usb = tmp_path / "usb"
    usb.mkdir()
    _make_usb_device(usb, "1-1", "2109", "3431")            # just a hub
    monkeypatch.setattr(usb_recovery, "USB_DEVICES_GLOB", str(usb / "*"))

    assert usb_recovery.camera_present() is False


def test_camera_present_is_case_insensitive(monkeypatch, tmp_path):
    usb = tmp_path / "usb"
    usb.mkdir()
    _make_usb_device(usb, "1-1.1", "291A", "3369")          # upper-case vendor
    monkeypatch.setattr(usb_recovery, "USB_DEVICES_GLOB", str(usb / "*"))

    assert usb_recovery.camera_present() is True


# -- xhci_pci_devices ---------------------------------------------------------
def test_xhci_pci_devices_returns_only_pci_symlinks(monkeypatch, tmp_path):
    driver = tmp_path / "xhci_hcd"
    driver.mkdir()
    targets = tmp_path / "targets"
    targets.mkdir()

    # A bound controller appears as a symlink named by its PCI address.
    (targets / "ctrl").mkdir()
    os.symlink(targets / "ctrl", driver / "0000:01:00.0")
    # The driver's own attribute files carry no ":" and must be ignored.
    (driver / "bind").write_text("")
    (driver / "unbind").write_text("")
    (driver / "uevent").write_text("")
    monkeypatch.setattr(usb_recovery, "XHCI_DRIVER_DIR", str(driver))

    assert usb_recovery.xhci_pci_devices() == ["0000:01:00.0"]


def test_xhci_pci_devices_empty_when_none_bound(monkeypatch, tmp_path):
    driver = tmp_path / "xhci_hcd"
    driver.mkdir()
    (driver / "bind").write_text("")
    monkeypatch.setattr(usb_recovery, "XHCI_DRIVER_DIR", str(driver))

    assert usb_recovery.xhci_pci_devices() == []


# -- _base_block_name ---------------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("mmcblk0p2", "mmcblk0"),
    ("mmcblk0", "mmcblk0"),
    ("nvme0n1p1", "nvme0n1"),
    ("nvme0n1", "nvme0n1"),
    ("sda2", "sda"),
    ("sda", "sda"),
    ("vdb3", "vdb"),
])
def test_base_block_name(name, expected):
    assert usb_recovery._base_block_name(name) == expected


# -- _root_on_usb -------------------------------------------------------------
def _wire_root_device(monkeypatch, tmp_path, mounts_text, block_name, real_segments):
    '''Point PROC_MOUNTS + SYS_BLOCK at a fake tree where `block_name` resolves
    through a path made of `real_segments` (e.g. ("scb", "usb1", "1-1") for a USB
    SSD, or ("emmc2bus", "mmc0") for the SD card).'''
    mounts = tmp_path / "mounts"
    mounts.write_text(mounts_text)
    sysblock = tmp_path / "block"
    sysblock.mkdir()
    target = tmp_path.joinpath("devices", *real_segments, block_name)
    target.mkdir(parents=True)
    os.symlink(target, sysblock / block_name)
    monkeypatch.setattr(usb_recovery, "PROC_MOUNTS", str(mounts))
    monkeypatch.setattr(usb_recovery, "SYS_BLOCK", str(sysblock))


def test_root_on_usb_false_for_sdcard(monkeypatch, tmp_path):
    _wire_root_device(
        monkeypatch, tmp_path,
        "/dev/mmcblk0p2 / ext4 rw 0 0\n/dev/mmcblk0p1 /boot/firmware vfat rw 0 0\n",
        "mmcblk0", ("platform", "emmc2bus", "mmc0"),
    )
    assert usb_recovery._root_on_usb() is False


def test_root_on_usb_true_for_usb_ssd(monkeypatch, tmp_path):
    _wire_root_device(
        monkeypatch, tmp_path,
        "/dev/sda2 / ext4 rw 0 0\n",
        "sda", ("platform", "scb", "usb1", "1-1"),
    )
    assert usb_recovery._root_on_usb() is True


# -- reenumerate_usb ----------------------------------------------------------
def test_reenumerate_usb_unbinds_then_binds(monkeypatch):
    writes = []
    monkeypatch.setattr(usb_recovery, "xhci_pci_devices", lambda: ["0000:01:00.0"])
    monkeypatch.setattr(
        usb_recovery, "_write_sysfs",
        lambda path, value: writes.append((path, value)) or True,
    )
    monkeypatch.setattr(usb_recovery.time, "sleep", lambda seconds: None)

    assert usb_recovery.reenumerate_usb() is True
    assert writes == [
        (os.path.join(usb_recovery.XHCI_DRIVER_DIR, "unbind"), "0000:01:00.0"),
        (os.path.join(usb_recovery.XHCI_DRIVER_DIR, "bind"), "0000:01:00.0"),
    ]


def test_reenumerate_usb_skips_bind_when_unbind_fails(monkeypatch):
    writes = []

    def fake_write(path, value):
        writes.append((path, value))
        return not path.endswith("unbind")     # unbind "fails"

    monkeypatch.setattr(usb_recovery, "xhci_pci_devices", lambda: ["0000:01:00.0"])
    monkeypatch.setattr(usb_recovery, "_write_sysfs", fake_write)
    monkeypatch.setattr(usb_recovery.time, "sleep", lambda seconds: None)

    usb_recovery.reenumerate_usb()
    # bind must not be attempted after a failed unbind.
    assert writes == [(os.path.join(usb_recovery.XHCI_DRIVER_DIR, "unbind"), "0000:01:00.0")]


def test_reenumerate_usb_false_when_no_controllers(monkeypatch):
    monkeypatch.setattr(usb_recovery, "xhci_pci_devices", lambda: [])
    assert usb_recovery.reenumerate_usb() is False


# -- recover_camera (orchestration) -------------------------------------------
def test_recover_camera_noop_when_present(monkeypatch):
    monkeypatch.setattr(usb_recovery, "camera_present", lambda: True)
    attempted = []
    monkeypatch.setattr(
        usb_recovery, "reenumerate_usb", lambda: attempted.append("reset") or True)

    result = usb_recovery.recover_camera()

    assert result == {"recovered": True, "action": "none"}
    assert attempted == []                  # never touches USB when it's fine


def test_recover_camera_aborts_when_root_on_usb(monkeypatch):
    monkeypatch.setattr(usb_recovery, "camera_present", lambda: False)
    monkeypatch.setattr(usb_recovery, "_root_on_usb", lambda: True)
    attempted = []
    monkeypatch.setattr(
        usb_recovery, "reenumerate_usb", lambda: attempted.append("reset") or True)

    result = usb_recovery.recover_camera()

    assert result["recovered"] is False
    assert result["action"] == "aborted"
    assert attempted == []                  # the safety guard blocks the reset


def test_recover_camera_success(monkeypatch):
    monkeypatch.setattr(usb_recovery, "camera_present", lambda: False)
    monkeypatch.setattr(usb_recovery, "_root_on_usb", lambda: False)
    monkeypatch.setattr(usb_recovery, "reenumerate_usb", lambda: True)
    monkeypatch.setattr(usb_recovery, "_wait_for_camera", lambda: True)
    restarted = []
    monkeypatch.setattr(
        usb_recovery, "_restart_camera_service", lambda: restarted.append(True))

    result = usb_recovery.recover_camera()

    assert result == {"recovered": True, "action": "reset"}
    assert restarted == [True]              # service restarted to drop stale cache


def test_recover_camera_still_absent_after_reset(monkeypatch):
    monkeypatch.setattr(usb_recovery, "camera_present", lambda: False)
    monkeypatch.setattr(usb_recovery, "_root_on_usb", lambda: False)
    monkeypatch.setattr(usb_recovery, "reenumerate_usb", lambda: True)
    monkeypatch.setattr(usb_recovery, "_wait_for_camera", lambda: False)
    monkeypatch.setattr(usb_recovery, "_restart_camera_service", lambda: None)

    result = usb_recovery.recover_camera()

    assert result["recovered"] is False
    assert result["action"] == "reset"


def test_recover_camera_reports_reset_failure(monkeypatch):
    monkeypatch.setattr(usb_recovery, "camera_present", lambda: False)
    monkeypatch.setattr(usb_recovery, "_root_on_usb", lambda: False)
    monkeypatch.setattr(usb_recovery, "reenumerate_usb", lambda: False)

    result = usb_recovery.recover_camera()

    assert result == {"recovered": False, "action": "reset-failed"}
