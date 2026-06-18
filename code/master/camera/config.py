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
_master_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _master_dir not in sys.path:
    sys.path.append(_master_dir)


# Loopback bind: nginx fronts this at /camera/ and pins 127.0.0.1 (never
# "localhost", which also resolves to ::1 and would intermittently 502 against an
# IPv4-only bind — see the note in install/assets/tethys-web.nginx).
HOST = '127.0.0.1'
PORT = 8002

# Snapshot capture format. The verified USB cam (Anker PowerConf C200) emits MJPG
# natively at this size, so a grab needs no transcoding.
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720

# Frames to discard before the kept one, so auto-exposure / white-balance have a
# few frames to converge — a cold UVC device's first frame is often dark or
# green-tinted.
CAPTURE_SKIP_FRAMES = 2

# Hard ceiling (seconds) on a single grab, so a wedged device can never block the
# request thread indefinitely.
CAPTURE_TIMEOUT_SECONDS = 5

# Privacy guards, mirroring the pump auto-off philosophy:
#  - idle: release the device if the UI stops fetching (browser closed/asleep).
#  - max-on: a hard ceiling so the camera can never be left on indefinitely.
IDLE_TIMEOUT_SECONDS = 15
MAX_ON_SECONDS = 30 * 60

# Hint sent to the UI for its snapshot refresh cadence (seconds). Comfortably
# under IDLE_TIMEOUT_SECONDS so normal polling keeps the device warm and never
# trips the idle auto-off.
SNAPSHOT_REFRESH_SECONDS = 3


# =============================================================================
def get_api_key():
    '''Return the shared TETHYS_API_KEY from the git-ignored globals/secrets.py —
    the same key the Django API gates on (api/tethys_api/permissions.py). Returns
    None if it is unset or unreadable, so the service fails closed (every keyed
    request is then rejected).'''
    try:
        from globals.secrets import TETHYS_API_KEY
        return TETHYS_API_KEY
    except Exception:
        return None
