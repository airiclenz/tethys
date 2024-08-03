from time import sleep
from datetime import datetime, date, timedelta
import RPi.GPIO as GPIO

from hardware import Pins
import apiInterface as api
import channel as hardwareChannel
from globals import *


# =============================================================================
def handleActions():
    if api.isInSilentPhase():
        return

    counter = 0

    for flag in FlagHandler().channelFlags:
        if flag == True:
            handleChannelAction(counter + 1)
            FlagHandler.channelFlags[counter] = False
            flag = False

        counter += 1


# =============================================================================
def handleChannelAction(channelNumber):
    # Load the channel summaries to see if we need to perform an action
    channelSummary = api.loadChannelSummary(channelNumber)

    if channelSummary == None:
        print("---------------------------")
        print(
            "Could not retrieve data for checking if actions are due on channel",
            channelNumber,
        )
        return

    if channelSummary["enabled"] == True:
        moistureLevel = channelSummary["sensorData_lastMoisturePercent"]
        triggerLevel = channelSummary["actionTriggerPercent"]
        pumpDuration = channelSummary["pumpDurationSeconds"]

        # do we need to pump and are we allowed to?
        if moistureLevel < triggerLevel:
            print("---------------------------")
            print("Pumping for channel", channelNumber, "initiated")

            startTime = datetime.now()

            hardwareChannel.activateChannel(channelNumber)
            sleep(pumpDuration)
            hardwareChannel.deactivateChannel(channelNumber)

            endTime = datetime.now()

            print("Pumping for", pumpDuration, "sec finsished.")

            api.createPumpActionInDB(channelNumber, startTime, endTime)
