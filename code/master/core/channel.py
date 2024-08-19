#import RPi.GPIO as GPIO
import lgpio
from time import sleep
from hardware import Pins
import apiInterface as api


# =============================================================================
def setOutputState(
        channelNumber: int, 
        type: str,
        state: bool):

    print(f"channel.setOutputState(channelNumber={channelNumber}, type={type}, state={state}) called")

    # convert to int - in case it comes as a string
    channelNumber = int(channelNumber)

    pinChannel = Pins.CHANNELS[channelNumber - 1]
    pinPump = Pins.PUMP

    try:

        # Initialize the GPIO chip
        chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(chip, pinChannel)
        lgpio.gpio_claim_output(chip, pinPump)

        newPinState = int(state)

        if type == 'valve':
            lgpio.gpio_write(chip, pinChannel, newPinState)
            lgpio.gpio_write(chip, pinPump, newPinState)

        else:
            lgpio.gpio_write(chip, pinChannel, newPinState)

        # Close the GPIO chip
        lgpio.gpiochip_close(chip)

    except lgpio.error as e:

        print(f"Error setting GPIO state: {e}")

    return True



