import os
import sys
import apiInterface as api
from colorama import Fore
from pumpController import PumpError

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from globals.logger import Logger


_logger = Logger(Fore.MAGENTA)

# Manual "Test Channel" activate requests older than this are ignored (marked
# expired) rather than run. This stops a tap made while the core was down -- e.g.
# during the nightly watchdog restart -- from silently energising a channel
# minutes later when the core comes back. Generously larger than one loop pass
# (the ~30s radio-listen window) so a genuine tap is never dropped.
MANUAL_COMMAND_MAX_AGE_SECONDS = 120


# =============================================================================
def drain(pumpController):
    '''Run every pending manual command through the pump controller. Because the
    controller is the single owner of the watering GPIO and enforces
    max_concurrent=1, a manual activate is rejected whenever another channel is
    already running -- so "one channel + pump at a time" holds for manual taps
    exactly as it does for automatic watering.

    Manual taps deliberately do NOT honour the silent-phase (quiet-hours) gate
    that actionEngine applies to automatic watering: the web "Test Channel"
    toggle is an explicit operator override for diagnostics, so it runs
    regardless of the schedule. Do not add an isInSilentPhase() check here.'''
    for command in api.fetchPendingManualCommands():
        _handleCommand(command, pumpController)


# =============================================================================
def _handleCommand(command, pumpController):

    commandId = command["id"]
    channel = command["channel"]
    channelType = command["channelType"]
    action = command["action"]

    if action == "activate":
        _activate(commandId, channel, channelType, command["ageSeconds"], pumpController)

    elif action == "deactivate":
        _deactivate(commandId, channel, channelType, pumpController)

    else:
        _logger.log(f"Manual command {commandId}: unknown action '{action}'.")
        api.reportManualCommandResult(commandId, "failed", f"unknown action '{action}'")


# =============================================================================
def _activate(commandId, channel, channelType, ageSeconds, pumpController):

    # Ignore a stale tap rather than energise a channel the user no longer expects.
    if ageSeconds > MANUAL_COMMAND_MAX_AGE_SECONDS:
        _logger.log(f"Manual activate {commandId} on channel {channel} expired ({int(ageSeconds)}s old).")
        api.reportManualCommandResult(commandId, "expired", "request was too old to run")
        return

    try:
        handle = pumpController.activate(channel, channelType)
    except (ValueError, PumpError) as e:
        _logger.log(f"Manual activate {commandId} on channel {channel} failed: {e}")
        api.reportManualCommandResult(commandId, "failed", str(e))
        return

    if handle is None:
        # max_concurrent reached: another channel is already running. This is the
        # power-limit guard surfacing -- the UI reverts the toggle on "rejected".
        _logger.log(f"Manual activate {commandId} on channel {channel} rejected (another channel active).")
        api.reportManualCommandResult(commandId, "rejected", "another channel is already active")
    else:
        _logger.log(f"Manual activate {commandId} on channel {channel} accepted.")
        api.reportManualCommandResult(commandId, "accepted", "")


# =============================================================================
def _deactivate(commandId, channel, channelType, pumpController):

    try:
        succeeded = pumpController.deactivate(channel, channelType)
    except ValueError as e:
        _logger.log(f"Manual deactivate {commandId} on channel {channel} failed: {e}")
        api.reportManualCommandResult(commandId, "failed", str(e))
        return

    if succeeded:
        api.reportManualCommandResult(commandId, "done", "")
    else:
        api.reportManualCommandResult(commandId, "failed", "GPIO write failed")
