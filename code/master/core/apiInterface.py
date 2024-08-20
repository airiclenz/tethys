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


_logger = Logger(Fore.BLUE)
_logger.increaseIndent()


# =============================================================================
def loadChannel(channelNumber):
    # Load the channel data to see if we need to perform an action
    url = BASE_API_URL + "channel/" + str(channelNumber)
    response = requests.get(url)

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
    response = requests.get(url)

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
    response = requests.get(url)

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
        response = requests.get(url)
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
        "actionType": "pump",
        "startTime": startTime.strftime(DATETIME_FORMAT),
        "endTime": endTime.strftime(DATETIME_FORMAT),
    }

    response = requests.post(url=callUrl, json=jsonBody)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        _logger.log("The action was successfully logged in the database.")

    else:
        _logger.log("ERROR: The action could not be logged in the database!")
