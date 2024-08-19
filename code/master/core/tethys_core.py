from __future__ import print_function

import sys
import os

# import lgpio
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


'''
chip = lgpio.gpiochip_open(0)

lgpio.gpio_claim_outputtup(chip, Pins.PUMP)
lgpio.gpio_claim_output(chip, Pins.CHANNELS[0])
lgpio.gpio_claim_output(chip, Pins.CHANNELS[1])
lgpio.gpio_claim_output(chip, Pins.CHANNELS[2])
lgpio.gpio_claim_output(chip, Pins.CHANNELS[3])
lgpio.gpio_claim_output(chip, Pins.CHANNELS[4])
'''

radioWrapper = Radio()
radioWrapper.initializeRadio()


print("Tethys Core started...")

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:

    radioWrapper.handleRadioEvents(timeOutInSec = 30)

    # see if there is anything to do.
    actionEngine.handleActions(radioWrapper)


