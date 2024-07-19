import os
import json
import logging
import datetime
import requests
import platform

from datetime import datetime, timedelta
from web import settings
from urllib.parse import urlparse
from gpiozero import CPUTemperature

logging.basicConfig(encoding="utf-8", level=logging.INFO)


# =============================================================================
def log(message):
    now = datetime.now()
    dateString = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    logging.info(
        settings.LOGGING_INDENT_INNER
        + dateString
        + settings.LOGGING_INDENT_OUTER
        + message
    )


# =============================================================================
def getApiPathFromRequest(request):
    pathParts = urlparse(request.build_absolute_uri("/"))
    return pathParts.scheme + "://" + pathParts.hostname + settings.API_BASE


# =============================================================================
#def getCoreTemperature():
#    return CPUTemperature()


# =============================================================================
def getResponseForSensorSummary():
    response = requests.get(settings.API_URL + "channelSummary")

    return json.dumps({
        "responseType": "requestChannelSummary",
        "channelSummary": response.json()
    })

# =============================================================================
def getResponseForSchedules():
    response = requests.get(settings.API_URL + "schedule")

    return json.dumps({
        "responseType": "requestSchedules",
        "schedules": response.json()
    })


# =============================================================================
def getReponseForSystemStatus():

    plarformName = platform.system()

    cpuTemperature = 0.0
    coreServiceState = False

    if plarformName == "Darwin":
        cpuTemperature = None
        coreServiceState = None

    elif plarformName == "Linux":
        cpuTemperature = CPUTemperature().temperature
        coreServiceState = os.system("systemctl is-active --quiet tethys-core.service") == 0

    return json.dumps({
        "responseType": "requestSystemStatus",
        "coreTemperature": cpuTemperature,
        "coreServiceState": coreServiceState,
        "silentPhaseStatus": {
            "lastCalculationTime":"1900-01-01T00:00:00Z",
            "startTime":"1900-01-01T00:00:00Z",
            "endTime":"1900-01-01T00:00:00Z",
            "inPhase":False
        }
    })


# =============================================================================
def formatChannelSummaries(channelSummaries):
    resultList = []

    for channel in channelSummaries:
        resultItem = {}

        resultItem["number"] = channel["number"]
        resultItem["enabled"] = str(channel["enabled"]).lower()
        resultItem["channelType"] = channel["channelType"]
        resultItem["channelTypeValue"] = channel["channelTypeValue"]
        resultItem["actionTriggerPercent"] = channel["actionTriggerPercent"]
        resultItem["pumpDurationSeconds"] = channel["pumpDurationSeconds"]
        resultItem["nickName"] = channel["nickName"]
        resultItem["sensorMeasureFrequencyMinutes"] = channel[
            "sensorMeasureFrequencyMinutes"
        ]
        resultItem["sensorTransmissionPowerLevel"] = channel[
            "sensorTransmissionPowerLevel"
        ]
        resultItem["sensorTransmissionPowerLevelValue"] = channel[
            "sensorTransmissionPowerLevelValue"
        ]
        resultItem["sensorTriggerCalibration"] = str(
            channel["sensorTriggerCalibration"]
        ).lower()

        if channel["sensorData_count"] != None:
            resultItem["sensorData_count"] = channel["sensorData_count"]

            try:
                dataTimestamp = datetime.strptime(
                    channel["sensorData_lastTimestamp"], settings.DATETIME_FORMAT
                )
                resultItem["sensorData_lastTimestamp"] = dataTimestamp
            except:
                dataTimestamp = datetime.strptime(
                    channel["sensorData_lastTimestamp"],
                    settings.DATETIME_FORMAT_NO_MILL,
                )
                resultItem["sensorData_lastTimestamp"] = dataTimestamp

            resultItem["sensorData_lastMoisturePercent"] = (
                str(channel["sensorData_lastMoisturePercent"]) + " % moist"
            )
            resultItem["sensorData_lastBatteryVoltage"] = (
                "{:.2f}".format(channel["sensorData_lastBatteryVoltage"]) + " V"
            )

        else:
            resultItem["sensorData_count"] = "0"
            resultItem["sensorData_lastTimestamp"] = "--"
            resultItem["sensorData_lastMoisturePercent"] = "--"
            resultItem["sensorData_lastBatteryVoltage"] = "--"

        if channel["action_count"] != None:
            resultItem["action_count"] = channel["action_count"]

            try:
                actionTimestamp = datetime.strptime(
                    channel["action_lastStartTime"], settings.DATETIME_FORMAT
                )
                resultItem["action_lastStartTime"] = actionTimestamp
            except:
                actionTimestamp = datetime.strptime(
                    channel["action_lastStartTime"], settings.DATETIME_FORMAT_NO_MILL
                )
                resultItem["action_lastStartTime"] = actionTimestamp

            resultItem["action_lastActionType"] = channel["action_lastActionType"]

        else:
            resultItem["action_count"] = "0"
            resultItem["action_lastStartTime"] = "--"
            resultItem["action_lastActionType"] = "--"

        resultList.append(resultItem)

    return resultList


# =============================================================================
def getTransmissionPowerLabel(level):
    switcher = {0: "Min", 1: "Low", 2: "High", 3: "Max"}

    return switcher.get(level, "Invalid Power Level")


# =============================================================================
def getTimePassedSinceString(timestamp):
    elapsedTime = datetime.now() - timestamp
    totalSeconds = elapsedTime.total_seconds()

    days = divmod(totalSeconds, 86400)[0]
    totalSeconds = totalSeconds - (days * 86400)

    hours = divmod(totalSeconds, 3600)[0]
    totalSeconds = totalSeconds - (hours * 3600)

    minutes = divmod(totalSeconds, 60)[0]

    resultString = None

    if days > 0:
        yesterday = datetime.now() - timedelta(1)

        if timestamp.date() == yesterday.date():
            resultString = "yesterday " + timestamp.time().strftime("%H:%M")

        else:
            resultString = timestamp.strftime("%Y-%m-%d %H:%M")

    else:
        if hours > 0:
            resultString = f"{hours:.0f}" + "h " + f"{minutes:02.0f}" + "min ago"

        else:
            resultString = f"{minutes:.0f}" + " minutes ago"

    return resultString
