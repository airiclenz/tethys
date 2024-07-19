import json
import threading
import requests

from threading import Timer
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from web import tools, settings
import tethys_web.consumers as consumers


isPolling = False
channel = None
lastUpdateLocal = None
isSilentPhaseLocal = None
repeater = None


# ::::::::::::::::::::::::::::::::::::::::::
def startPolling():
    tools.log("Checking if polling needs to be started...")
    global isPolling
    global thread

    if isPolling == False:
        isPolling = True
        repeater = RepeatTimer(settings.POLL_FREQUENCY_SEC, checkForUpdate)
        repeater.start()
        tools.log("Polling started...")

    else:
        tools.log("Polling was running already.")


# ::::::::::::::::::::::::::::::::::::::::::
def checkForUpdate():
    global lastUpdateLocal
    global isSilentPhaseLocal
    global channel

    # -----------------------------------------
    # retrieve last Update
    try:
        responseLastUpdate = requests.get(settings.API_URL + "lastUpdate/")
        if responseLastUpdate.status_code != 200:
            return
    except requests.exceptions.RequestException:
        return

    if responseLastUpdate.status_code != 200:
        return

    lastUpdateDict = responseLastUpdate.json()
    timestampString = lastUpdateDict['timestamp']

    try:
        lastUpdate = datetime.strptime(
            timestampString, settings.DATETIME_FORMAT_NO_MILL
        )
    except:
        lastUpdate = datetime.strptime(timestampString, settings.DATETIME_FORMAT)

    # -----------------------------------------
    # retrieve silent phase status
    try:
        responseSilentPhaseStatus = requests.get(
            settings.API_URL + "silentPhaseStatus/"
        )
    except requests.exceptions.RequestException:
        return

    if responseSilentPhaseStatus.status_code != 200:
        return

    silentPhaseStatusDict = responseSilentPhaseStatus.json()
    isSilentPhase = silentPhaseStatusDict['inPhase']

    if lastUpdate != lastUpdateLocal or isSilentPhase != isSilentPhaseLocal:
        tools.log("Polling: Update found...")

        lastUpdateLocal = lastUpdate
        isSilentPhaseLocal = isSilentPhase

        # Send to group (broadcast)
        try:
            channel_layer = get_channel_layer()
            
            # TODO
            #sensorMessage = tools.getResponseForSensorSummary()
            scheduleMessage = tools.getResponseForSchedules()

            # answer to client
            #async_to_sync(channel_layer.group_send)(
            #    settings.CHANNEL_GROUP_NAME,
            #    { "type": "channelSummary", "message": sensorMessage },
            #)

            # answer to client
            async_to_sync(channel_layer.group_send)(
                settings.CHANNEL_GROUP_NAME,
                { "type": "scheduleSummary", "message": scheduleMessage },
            )

            tools.log("Polling: Updated data was sent.")

        except Exception as e: 
            tools.log("Failed to upload to ftp: " + str(e))
            pass


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
