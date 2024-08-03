#!/usr/bin/env python3

from __future__ import print_function

import sys
import os

from time import sleep
from datetime import datetime

from radio import Radio
import actionEngine

sys.path.append(os.path.abspath('../globals'))
from logger import Logger


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# This Service handels the interface to the nRF24L01+ module.
# It initializes an interrupt driven listening function that reacts to
# messages from the moisture sensors to the radio module of this master unit.

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


logger = Logger()
radio = Radio()

print("Tethys Core started...")
millis = lambda: datetime.now().microsecond


radio.initializeRadio()


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:
    # the IRQ pin takes care of everything so we can just sleep...
    # sleep for some time
    sleep(30)

    # see if there is anything to do.
    actionEngine.handleActions()
