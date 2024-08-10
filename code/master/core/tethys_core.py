#!/usr/bin/env python3

from __future__ import print_function

import sys
import os

from time import sleep
from datetime import datetime, timedelta

from hardware import Pins
from radio import Radio
import actionEngine



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


print("Tethys Core started...")
#millis = lambda: datetime.now().microsecond


radioWrapper.initializeRadio()


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:

    radioWrapper.handleRadioEvents(30)

    # see if there is anything to do.
    actionEngine.handleActions(radioWrapper)


