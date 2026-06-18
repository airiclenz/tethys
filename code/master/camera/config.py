# =============================================================================
# Camera service configuration.
#
# Small constants + the one place the shared TETHYS_API_KEY is read, kept apart
# from the controller/HTTP logic the same way core/config.py is. The camera
# service runs with WorkingDirectory=camera/, so only camera/ is on the import
# path; this module bootstraps the shared `globals` package onto sys.path (the
# same trick core/config.py uses) so the API key can be read from globals/secrets.
# =============================================================================

import os
import sys

# Make the shared `globals` package (code/master/globals) importable. This module
# is imported early, before any entry point appends the master dir, so do it here.
_master_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _master_dir not in sys.path:
    sys.path.append(_master_dir)


# Loopback bind: nginx fronts this at /camera/ and pins 127.0.0.1 (never
# "localhost", which also resolves to ::1 and would intermittently 502 against an
# IPv4-only bind — see the note in install/assets/tethys-web.nginx).
HOST = "127.0.0.1"
PORT = 8002

# Snapshot capture format. The verified USB cam (Anker PowerConf C200) emits MJPG
# natively at this size, so a grab needs no transcoding.
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720

# Frames to discard before the kept one, so auto-exposure / white-balance have a
# few frames to converge — a cold UVC device's first frame is often dark or
# green-tinted.
CAPTURE_SKIP_FRAMES = 2

# Frames to discard on a grab that *pins* focus (focus_absolute set). Two camera
# quirks make this necessary (both verified on the C200 via v4l2-ctl):
#   1. The camera resets focus_absolute to its default the moment a stream STOPS,
#      so every one-shot grab starts with the lens back at the default and has to
#      travel to the requested position again.
#   2. The focus motor only travels while a stream is ACTIVE, ~1 s for a full-range
#      move — so the lens must settle within this grab's own stream.
# A couple of skip frames catches the lens mid-travel (the frame looks unfocused /
# "hunting", which is the bug this fixes); ~30 frames (≈1 s @ 30 fps) lets a
# full-range move complete before the kept frame. Frame-based (not seconds) so it
# self-scales with the camera's actual frame rate. Used in place of
# CAPTURE_SKIP_FRAMES only for a focused grab; zoom is digital (instant, and not
# reset on stream stop) so an unfocused grab keeps the smaller CAPTURE_SKIP_FRAMES.
CAPTURE_FOCUS_SETTLE_SKIP_FRAMES = 30

# Seed defaults for the focus / zoom sliders the Webcam UI offers (the live knob
# is the slider; these are the starting positions a fresh browser sees, and the
# value applied to a snapshot that carries no per-request override — e.g. a curl).
#   None  -> leave the camera's own behaviour untouched (focus: continuous AF).
#   <int> -> pin the control: focus locks focus_absolute (disabling continuous AF
#            first, since it's ignored while AF owns the lens), so every frame is
#            at the same focal distance — no autofocus hunting / "breathing".
# Ranges are camera-specific; the UI reads each control's min/max from
# `v4l2-ctl --list-ctrls` and disables a slider the camera doesn't expose. A
# control absent from the camera is never sent, so an out-of-range/unsupported
# value can't wedge the grab.
CAPTURE_FOCUS = 550
CAPTURE_ZOOM = None

# Hard ceiling (seconds) on a single grab, so a wedged device can never block the
# request thread indefinitely.
CAPTURE_TIMEOUT_SECONDS = 5

# Privacy guards, mirroring the pump auto-off philosophy:
#  - idle: release the device if the UI stops fetching. The Webcam tab now keeps
#    the camera running while its tab is hidden (a quick app/tab switch shouldn't
#    kill the live view), so this window is deliberately wide enough to tolerate a
#    backgrounded/frozen tab whose snapshot polling has paused. Tradeoff: a browser
#    killed without a clean pagehide leaves the device on until this elapses.
#  - max-on: a hard ceiling so the camera can never be left on indefinitely.
# Both are 30 min, so max-on is the effective single timeout.
IDLE_TIMEOUT_SECONDS = 30 * 60
MAX_ON_SECONDS = 30 * 60

# Hint sent to the UI for its snapshot refresh cadence (seconds). Comfortably
# under IDLE_TIMEOUT_SECONDS so normal polling keeps the device warm and never
# trips the idle auto-off.
SNAPSHOT_REFRESH_SECONDS = 3


# =============================================================================
def get_api_key():
    """Return the shared TETHYS_API_KEY from the git-ignored globals/secrets.py —
    the same key the Django API gates on (api/tethys_api/permissions.py). Returns
    None if it is unset or unreadable, so the service fails closed (every keyed
    request is then rejected)."""
    try:
        from globals.secrets import TETHYS_API_KEY

        return TETHYS_API_KEY
    except Exception:
        return None
