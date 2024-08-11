from __future__ import print_function

import sys
import os

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
radioWrapper.initializeRadio()

print("Tethys Core started...")

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:

    radioWrapper.handleRadioEvents(timeOutInSec = 30)

    # see if there is anything to do.
    actionEngine.handleActions(radioWrapper)


