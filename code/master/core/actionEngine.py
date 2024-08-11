from time import sleep
from datetime import datetime, date, timedelta

from hardware import Pins
import apiInterface as api
import channel as hardwareChannel
from globals import *
from colorama import Fore
from logger import Logger

radioWrapper = None


_logger = Logger(Fore.YELLOW)


# =============================================================================
def handleActions(radioWrapperIn):
    
    global radioWrapper
    radioWrapper = radioWrapperIn

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
        _logger.log(f'Could not retrieve data for checking if actions are due on channel {channelNumber}')
        return

    channelEnabled = channelSummary["enabled"]
    moistureLevel = channelSummary["sensorData_lastMoisturePercent"]
    triggerLevel = channelSummary["actionTriggerPercent"]
    pumpDuration = channelSummary["pumpDurationSeconds"]

    # do we need to pump?
    if moistureLevel <= triggerLevel and channelEnabled:

        _logger.log(f'Pumping for channel {channelNumber} initiated ({pumpDuration} sec)')
        _logger.increaseIndent()

        startTime = datetime.now()

        hardwareChannel.activateChannel(channelNumber)
        radioWrapper.handleRadioEvents(pumpDuration)
        hardwareChannel.deactivateChannel(channelNumber)

        endTime = datetime.now()

        _logger.log(f'Pumping for {pumpDuration} sec finsished.')

        api.createPumpActionInDB(channelNumber, startTime, endTime)

        _logger.decreaseIndent()
