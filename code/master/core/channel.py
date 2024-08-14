import RPi.GPIO as GPIO
from time import sleep
from hardware import Pins
import apiInterface as api


# =============================================================================
def setOutputState(
        channelNumber: int, 
        type: str,
        state: bool):

    # convert to int - in case it comes as a string
    channelNumber = int(channelNumber)

    pinChannel = Pins.CHANNELS[channelNumber - 1]
    pinPump = Pins.PUMP

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pinChannel, GPIO.OUT)
    GPIO.setup(pinPump, GPIO.OUT)

    if state == True:
        newPinState = GPIO.HIGH
    else:
        newPinState = GPIO.LOW


    if type == 'valve':
        GPIO.output(pinChannel, newPinState)
        GPIO.output(pinPump, newPinState)

    else:
        GPIO.output(pinChannel, newPinState)

    return True


