from __future__ import print_function

import sys
import os
import atexit
import signal
import threading
import time

from hardware import Pins
from radio import Radio
from pumpController import make_controller


root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

import core.actionEngine as actionEngine
import core.manualCommands as manualCommands
import core.fanController as fan



# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# This Service handels the interface to the nRF24L01+ module.
# It initializes an interrupt driven listening function that reacts to
# messages from the moisture sensors to the radio module of this master unit.

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


radioWrapper = Radio()
radioWrapper.initializeRadio()

# Warm the config cache before we start serving GETCONFIG requests, so the very
# first sensor handshake after boot is answered from memory rather than a
# blocking HTTP GET inside the sensor's short listen window.
radioWrapper.refreshConfigCache()

# Single owner of the watering GPIO. Built once; drives all lines LOW on
# construction (fail-safe boot) and again on shutdown so a crash/restart can
# never leave a pump energised.
pumpController = make_controller()

def _shutdownPumps(*_args):
    pumpController.shutdown()

atexit.register(_shutdownPumps)
signal.signal(signal.SIGTERM, lambda *_: (_shutdownPumps(), sys.exit(0)))

print("Tethys Core started...")

# =============================================================================
def handleCoreActivities():

    while True:
        # Keep config replies cache-served and out of the radio response
        # window. Runs between listen windows, so its HTTP calls never delay a
        # sensor's handshake.
        radioWrapper.refreshConfigCache()
        radioWrapper.handleRadioEvents(timeOutInSec = 30)
        actionEngine.handleActions(pumpController)


# Manual taps drain on this cadence, on their own thread, independent of the 30s
# radio-listen window above -- so the web "Test Channel" toggle acts within ~1s
# instead of waiting for the current window to end.
MANUAL_DRAIN_INTERVAL_SEC = 1


# =============================================================================
def _drainManualCommands():
    while True:
        try:
            # Run any manual "Test Channel" taps from the web UI through the same
            # single pump controller as automatic watering, so the one-channel
            # power limit is enforced across both paths. The controller's lock
            # serialises this thread against actionEngine on the main thread.
            manualCommands.drain(pumpController)
        except Exception as e:
            # A transient error (e.g. an API blip) must not kill the thread and
            # silently end manual control -- log it and keep polling.
            print(f"manual-drain loop error: {e}")
        time.sleep(MANUAL_DRAIN_INTERVAL_SEC)


# =============================================================================
def main():

    # The core is synchronous at heart (blocking lgpio/radio busy-waits), so each
    # concurrent activity runs on its own daemon thread rather than an asyncio
    # task. (The previous asyncio.create_task(handleCoreActivities()) blocked
    # forever evaluating the sync while-loop, so the fan task was never even
    # created.) Daemon threads exit with the process; the SIGTERM/atexit hook
    # above still drives the pumps LOW on shutdown.
    threading.Thread(target=_drainManualCommands, daemon=True).start()
    threading.Thread(target=fan.control_fan, daemon=True).start()

    # Radio listening + automatic watering run on the main thread.
    handleCoreActivities()


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":

    main()