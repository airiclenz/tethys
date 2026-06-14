from __future__ import print_function

import sys
import os
import atexit
import signal
import asyncio

from hardware import Pins
from radio import Radio
from pumpController import make_controller


root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

import core.actionEngine as actionEngine
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


# =============================================================================
async def main():
        
    task_core = asyncio.create_task(handleCoreActivities())
    task_fan = asyncio.create_task(fan.control_fan())

    await asyncio.gather(task_core, task_fan)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":

    asyncio.run(main())