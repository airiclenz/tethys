from __future__ import print_function

import sys
import os
import asyncio

from hardware import Pins
from radio import Radio
import actionEngine
import fanController


sys.path.append(os.path.abspath('../globals'))


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


print("Tethys Core started...")

# =============================================================================
def handleCoreActivities():
    radioWrapper.handleRadioEvents(timeOutInSec = 30)
    actionEngine.handleActions(radioWrapper)


# =============================================================================
async def main():
    
    task_core = asyncio.create_task(handleCoreActivities())
    task_fan = asyncio.create_task(fanController.control_fan())
    
    try:

        while True:

            await task_core
            await task_fan

    finally:
        task_core.cancel()
        task_fan.cancel()


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":

    asyncio.run(main())