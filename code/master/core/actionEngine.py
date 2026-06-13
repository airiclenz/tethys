import os
import sys
import apiInterface as api
from config import *
from colorama import Fore
from pumpController import PumpError

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

# Now you can import hardware
from globals.logger import Logger


_logger = Logger(Fore.YELLOW)


# =============================================================================
def handleActions(pumpController):

    # Fail closed: if the silent-phase status is unknown (None -- e.g. the API
    # is unreachable), do NOT water. Treating an unknown state as "not silent"
    # previously let the engine water blind on possibly-stale state.
    silentPhase = api.isInSilentPhase()
    if silentPhase is None:
        _logger.log('Silent-phase status unknown (API unreachable); skipping watering this pass.')
        return
    if silentPhase:
        return

    counter = 0

    for flag in FlagHandler().channelFlags:
        if flag == True:
            handled = handleChannelAction(counter + 1, pumpController)
            # Only clear the flag if the action was actually handled. If the
            # controller was busy (deferred), leave the flag set so we retry on
            # the next loop pass.
            if handled:
                FlagHandler.channelFlags[counter] = False

        counter += 1


# =============================================================================
def handleChannelAction(channelNumber, pumpController):

    # Load the channel summaries to see if we need to perform an action
    channelSummary = api.loadChannelSummary(channelNumber)

    if channelSummary == None:
        _logger.log(f'Could not retrieve data for checking if actions are due on channel {channelNumber}')
        return True

    channelEnabled = channelSummary["enabled"]
    moistureLevel = channelSummary["sensorData_lastMoisturePercent"]
    triggerLevel = channelSummary["actionTriggerPercent"]
    pumpDuration = channelSummary["pumpDurationSeconds"]
    channelType = channelSummary["channelType"]

    # do we need to pump?
    if not (moistureLevel <= triggerLevel and channelEnabled):
        return True

    _logger.log(f'Pumping for channel {channelNumber} initiated ({pumpDuration} sec)')

    # The controller clamps the duration, guarantees the pump is switched off,
    # and logs the completed action to the DB from its timer callback (so the
    # core loop is not blocked and the radio keeps listening while pumping).
    try:
        handle = pumpController.run_pump(
            channelNumber,
            pumpDuration,
            channelType,
            on_complete=lambda startTime, endTime: api.createPumpActionInDB(
                channelNumber, startTime, endTime,
            ),
        )
    except (ValueError, PumpError) as e:
        _logger.log(f'ERROR: could not pump channel {channelNumber}: {e}')
        return True  # don't hot-loop on a hardware/config error

    if handle is None:
        # Controller busy (max concurrent pumps reached) — retry next pass.
        return False

    return True
