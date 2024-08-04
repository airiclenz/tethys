import requests
import json
from globals import *


# =============================================================================
def loadChannel(channelNumber):
    # Load the channel data to see if we need to perform an action
    url = BASE_API_URL + "channel/" + str(channelNumber)
    response = requests.get(url)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        dataDict = json.loads(response.text)
        channel = dataDict["channel"]

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
        dataDict = json.loads(response.text)
        summary = dataDict["channelSummary"]

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
        print("The Tethys API is not reachable.")
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
    callUrl = BASE_API_URL + "action/" + str(channelNumber)

    formattedStartTime = startTime.strftime("%Y-%m-%d %H:%M:%S")
    formattedEndTime = endTime.strftime("%Y-%m-%d %H:%M:%S")

    jsonBody = {
        "actionType": "pumping",
        "startTime": formattedStartTime,
        "endTime": formattedEndTime,
    }

    response = requests.post(url=callUrl, json=jsonBody)

    # check if the response code is in the 200 range: 2xx
    responseCode = response.status_code - (response.status_code % 100)

    if responseCode == 200:
        print("The action was successfully logged in the database.")

    else:
        print("ERROR: The action could not be logged in the database!")
