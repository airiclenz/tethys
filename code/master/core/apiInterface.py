import os
import sys
import requests
import json
from config import *
from colorama import Fore

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)
    
# Now you can import hardware
from globals.logger import Logger
from globals.secrets import TETHYS_API_KEY


_logger = Logger(Fore.BLUE)
_logger.increaseIndent()

# Sent on mutating API calls; the API gates POST/PUT/PATCH/DELETE behind this key.
_AUTH_HEADERS = {"X-API-Key": TETHYS_API_KEY}


# =============================================================================
def loadChannel(channelNumber):
    # Load the channel data to see if we need to perform an action
    url = BASE_API_URL + "channel/" + str(channelNumber)
    response = requests.get(url, headers=_AUTH_HEADERS)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        channel = json.loads(response.text)
        return channel

    else:
        return None


# =============================================================================
def loadChannelSummary(channelNumber):
    # Load the channel summary to see if we need to perform an action
    url = BASE_API_URL + "channelSummary/" + str(channelNumber)
    response = requests.get(url, headers=_AUTH_HEADERS)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        summary = json.loads(response.text)
        return summary

    else:
        return None


# =============================================================================
def loadAllChannelSummaries():
    # Load the channel summaries to see if we need to perform an action
    url = BASE_API_URL + "channelSummary/"
    response = requests.get(url, headers=_AUTH_HEADERS)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        dataDict = json.loads(response.text)
        summaries = dataDict["channelSummary/"]

        return summaries

    else:
        return None


# =============================================================================
def isInSilentPhase():

    url = BASE_API_URL + "silentPhaseStatus/" + TIME_ZONE.replace('/', '-')

    try:
        response = requests.get(url, headers=_AUTH_HEADERS)
    except:
        _logger.log("The Tethys API is not reachable.")
        return None

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        status = json.loads(response.text)

        return status["inPhase"]

    else:
        return None


# =============================================================================
def createPumpActionInDB(channelNumber, startTime, endTime):
    
    callUrl = BASE_API_URL + "actionLog/"

    jsonBody = {
        "channel": channelNumber,
        # ISO-8601 with the UTC offset (the clock is timezone-aware UTC), so the
        # API stores the real instants. A bare DATETIME_FORMAT string carries no
        # offset and the API would treat it as local-time-mislabeled-as-UTC.
        "actionType": "pump",
        "startTime": startTime.isoformat(),
        "endTime": endTime.isoformat(),
    }

    response = requests.post(url=callUrl, json=jsonBody, headers=_AUTH_HEADERS)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        _logger.log("The action was successfully logged in the database.")

    else:
        _logger.log("ERROR: The action could not be logged in the database!")


# =============================================================================
def fetchPendingManualCommands():
    '''Return the pending manual activate/deactivate commands (oldest first) the
    web UI enqueued, as a list of dicts. Returns [] when there are none or the
    API is unreachable, so a missing API just defers manual control safely.'''
    url = BASE_API_URL + "manualCommand/pending"

    try:
        response = requests.get(url, headers=_AUTH_HEADERS)
    except requests.RequestException:
        _logger.log("The Tethys API is not reachable; manual commands skipped this pass.")
        return []

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        return json.loads(response.text)["manualCommands"]

    return []


# =============================================================================
def reportManualCommandResult(commandId, resultStatus, message=""):
    '''Write the terminal outcome of a processed manual command back to the API
    so the web UI can confirm or revert its toggle.'''
    url = BASE_API_URL + "manualCommand/" + str(commandId)
    jsonBody = {"status": resultStatus, "message": message}

    try:
        response = requests.patch(url=url, json=jsonBody, headers=_AUTH_HEADERS)
    except requests.RequestException:
        _logger.log(f"ERROR: could not report manual command {commandId} (API unreachable).")
        return

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode != 200:
        _logger.log(f"ERROR: reporting manual command {commandId} failed ({response.status_code}).")
