import RPi.GPIO as GPIO
from time import sleep
from hardware import Pins
import apiInterface as api


# =============================================================================
def activateChannel(channelNumber):
    channelData = api.loadChannel(channelNumber)

    isEnabled = channelData["enabled"]
    isValve = channelData["channelType"] == "valve"

    if not isEnabled:
        return False;

    pinChannel = Pins.CHANNELS[channelNumber - 1]
    pinPump = Pins.PUMP

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pinChannel, GPIO.OUT)
    GPIO.setup(pinPump, GPIO.OUT)

    if isValve:
        GPIO.output(pinChannel, GPIO.HIGH)
        GPIO.output(pinPump, GPIO.HIGH)

    else:
        GPIO.output(pinChannel, GPIO.HIGH)

    return True


# =============================================================================
def deactivateChannel(channelNumber):
    channelData = api.loadChannel(channelNumber)

    pinChannel = Pins.CHANNELS[channelNumber - 1]
    pinPump = Pins.PUMP
    isValve = channelData["channelType"] == "valve"

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pinChannel, GPIO.OUT)
    GPIO.setup(pinPump, GPIO.OUT)

    if isValve:
        GPIO.output(pinPump, GPIO.LOW)
        # we leave the valve open so the water can return to the bucket
        sleep(20)
        GPIO.output(pinChannel, GPIO.LOW)

    else:
        GPIO.output(pinPump, GPIO.LOW)
        GPIO.output(pinChannel, GPIO.LOW)

    # this seems to interfere with the RF Module as it is switching
    # off all the pins - so it is here just for reference:
    # GPIO.cleanup()

    return True
