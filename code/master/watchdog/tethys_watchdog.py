#!/usr/bin/env python3

import schedule
import time
import os
import sys
import logging


# usb_recovery reports via the stdlib logging module. Without a root config its
# INFO/WARNING detail from the in-process auto-heal path below is dropped (only a
# last-resort WARNING+ handler would fire); configure logging to stderr so the
# systemd journal captures the full unattended-recovery story.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# Make the shared `globals` package (code/master/globals) importable. The unit
# runs with WorkingDirectory=watchdog/, so only watchdog/ is on the import path;
# append the master dir so we can reach globals.usb_recovery (same trick the
# camera service uses in camera/config.py).
_master_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _master_dir not in sys.path:
    sys.path.append(_master_dir)

# The camera auto-heal is an OPTIONAL feature; the watchdog's core job is the
# daily service restart + journal vacuum. A failure to import usb_recovery must
# therefore degrade (skip the auto-heal) rather than take the whole watchdog down
# with it. Broad except on purpose: any import-time failure should disable just
# the feature, never the safety loop.
try:
    from globals.usb_recovery import camera_present, recover_camera
    _camera_recovery_available = True
except Exception as error:
    _camera_recovery_available = False
    print(f"Camera auto-heal disabled: usb_recovery import failed ({error}).")


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# This Service checks the other services of tethys. The core service is
# restarted every 24h. The USB webcam is also watched continuously: it can
# EPROTO-crash and drop off the bus mid-session (the Anker C200), and once it's
# gone only a USB controller re-enumeration brings it back — which this root
# service can do (the unprivileged camera service cannot).

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


# /////////////////////////////////////////////////////////////////////////////
def restartServices():
    # Absolute binary paths are required: the systemd unit pins PATH to the venv
    # bin (Environment=PATH=.../env_tethys/bin), so os.system()'s /bin/sh cannot
    # resolve bare "systemctl"/"journalctl" — it logged "not found" and this
    # function still printed success. Same fix as the /api/reboot/ endpoint.
    api = os.system("/usr/bin/systemctl restart tethys-api.service")
    core = os.system("/usr/bin/systemctl restart tethys-core.service")
    camera = os.system("/usr/bin/systemctl restart tethys-camera.service")

    if api == 0 and core == 0 and camera == 0:
        print("Services were restarted.")
    else:
        print(f"Service restart FAILED (api={api}, core={core}, camera={camera}).")

    vac = os.system("/usr/bin/journalctl --vacuum-time=1d")

    print("Services-journals were truncated." if vac == 0
          else f"Journal vacuum FAILED ({vac}).")


# /////////////////////////////////////////////////////////////////////////////
# Camera auto-heal.
#
# A controller re-enumeration is cheap and safe here (only the camera is on USB),
# but a genuinely unplugged / dead camera must not trigger a reset every minute.
# So recovery is rate-limited with an exponential back-off keyed on consecutive
# failures: attempt immediately on the first miss, then wait 5, 10, 20, 40, 60…
# minutes (capped) before each further attempt. A camera that returns resets the
# back-off, so a fresh drop is always recovered promptly.
RECOVERY_MIN_INTERVAL = 5 * 60        # shortest gap between attempts (seconds)
RECOVERY_MAX_INTERVAL = 60 * 60       # back-off cap (seconds)

_recovery = {"last_attempt": None, "failures": 0}


def _backoff_seconds(failures):
    if failures <= 0:
        return 0
    return min(RECOVERY_MIN_INTERVAL * (2 ** (failures - 1)), RECOVERY_MAX_INTERVAL)


def checkCamera():
    '''Every minute: if the webcam is no longer on the USB bus, re-enumerate to
    recover it — subject to the back-off above. Cheap when the camera is fine (a
    few sysfs reads).'''
    if camera_present():
        if _recovery["failures"]:
            print("Camera is back on the USB bus.")
        _recovery["failures"] = 0
        _recovery["last_attempt"] = None
        return

    now = time.monotonic()
    last = _recovery["last_attempt"]
    wait = _backoff_seconds(_recovery["failures"])
    if last is not None and (now - last) < wait:
        return                        # still backing off from the last attempt

    print(f"Camera missing from the USB bus; attempting recovery "
          f"(prior failures: {_recovery['failures']}).")
    _recovery["last_attempt"] = now
    result = recover_camera()

    if result.get("recovered"):
        _recovery["failures"] = 0
        print("Camera recovery succeeded.")
    else:
        _recovery["failures"] += 1
        next_wait = _backoff_seconds(_recovery["failures"])
        print(f"Camera recovery did not restore the device "
              f"({result.get('action')}); next attempt in ~{next_wait // 60} min.")


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
schedule.every().day.at("01:00").do(restartServices)
if _camera_recovery_available:
    schedule.every(1).minutes.do(checkCamera)
else:
    print("Camera auto-heal not scheduled (usb_recovery unavailable).")


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:
    schedule.run_pending()

    # the scheduler takes care of everything so we can just sleep...
    # sleep for one minute
    time.sleep(60)
