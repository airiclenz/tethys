import os
import sys

# usb_recovery is imported as `globals.usb_recovery` (a namespace package). The
# running services reach it by appending the master dir to sys.path (see
# camera/config.py and watchdog/tethys_watchdog.py); do the same here so the test
# imports resolve when run as `pytest globals/tests` from code/master/.
MASTER_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if MASTER_DIR not in sys.path:
    sys.path.insert(0, MASTER_DIR)
