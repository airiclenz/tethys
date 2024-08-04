import RPi.GPIO as GPIO
from struct import pack, unpack
from datetime import datetime
import numpy as np

# from RF24 import *

from pyrf24 import *

#import pigpio
#from nrf24 import *

import requests
from requests.exceptions import ConnectionError
from hardware import Pins

from globals import *



DATATYPE_SENSORDATA = 0
DATATYPE_SENSORDATA_BATTERYALERT = 1

# MASTER --> SENSOR:	Trigger Calibration
DATATYPE_CMD_CALIBRATE = 5

# SENSOR --> MASTER: 	Request the Configuration
DATATYPE_CMD_GETCONFIG = 6
DATATYPE_CONFIG = 7


# =============================================================================
# =============================================================================
# =============================================================================
class Radio:
    _pipeAddresses = [
        0x5232443230,
        0x5232443231,
        0x5232443232,
        0x5232443233,
        0x5232443234,
        0x5232443235,
    ]

    # =============================================================================
    def __init__(self):
        
        CSN_PIN = 0  # aka CE0 on SPI bus 0: /dev/spidev0.0
        if RF24_DRIVER == "MRAA":
            CE_PIN = 15  # for GPIO22
        elif RF24_DRIVER == "wiringPi":
            CE_PIN = 3  # for GPIO22
        else:
            CE_PIN = 22
        self.radio = RF24(CE_PIN, CSN_PIN)

        # self.radio = RF24(Pins.CE, Pins.CSN)
        # self.logger = Logger()

    # =============================================================================
    def initializeRadio(self):
        
        self.radio.begin()

        self.radio.setAddressWidth(5)
        self.radio.setRetries(10, 10)
        self.radio.setAutoAck(1)
        self.radio.setCRCLength(RF24_CRC_8)
        self.radio.setPALevel(RF24_PA_LOW)

        

        print("///////////////////////////////////////////////////")
        self.radio.printDetails()
        print("///////////////////////////////////////////////////")

        # set up callback for irq pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Pins.IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(Pins.IRQ, GPIO.FALLING, callback=self.checkRadioInbox)

        # setting up the reading- and writing pites
        self.radio.openWritingPipe(self._pipeAddresses[0])

        self.radio.openReadingPipe(1, self._pipeAddresses[1])
        self.radio.openReadingPipe(2, self._pipeAddresses[2])
        self.radio.openReadingPipe(3, self._pipeAddresses[3])
        self.radio.openReadingPipe(4, self._pipeAddresses[4])
        self.radio.openReadingPipe(5, self._pipeAddresses[5])

        self.radio.startListening()

    # =============================================================================
    def checkRadioInbox(self, irqPin):
        if self.radio.available() == True:
            print("---------------------------")

            pipeNo = self.radio.available_pipe()[1]

            print("Incoming from Pipe:", pipeNo)

            if pipeNo < 1 or pipeNo > 5:
                print("Invalid pipe number!")
                return

            while self.radio.available():
                len = self.radio.getDynamicPayloadSize()

                payload = self.radio.read(len)

            # handle what we received
            self.handlePayload(pipeNo, payload)


    # =============================================================================
    def handlePayload(self, channelNo, payload):
        # stop listening so we can send the appropriate answer
        self.radio.stopListening()

        command = payload[0]

        # the sensor requested the configuration
        if command == DATATYPE_CMD_GETCONFIG:
            print("Config was requested.")
            self.sendConfig(channelNo)

        elif command == DATATYPE_SENSORDATA:
            print("Sensordata received.")

            package = Radio.PackageSensorData(payload)

            # formatting the voltage
            voltageFormatted = "%.2f" % package.batteryVoltage

            print("Moisture:          ", package.moistureLevel, "%")
            print("Battery Voltage:   ", voltageFormatted, "V")

            dataset_json = {
                "batteryVoltage": package.batteryVoltage,
                "moisturePercent": package.moistureLevel,
            }

            url = BASE_API_URL + "sensordata/" + str(channelNo)

            try:
                response = requests.post(url, json=dataset_json)

                # check if the response code is in the 200 range: 2xx
                responseCode = response.status_code - (response.status_code % 100)

                if responseCode == 200:
                    print("Data was succesfully saved to the API.")

                    FlagHandler().channelFlags[channelNo - 1] = True

                else:
                    print("There was an error saving the data: ", response.reason)

            except ConnectionError:
                print("ERROR: The API is not reachable!", url)

        # Now, resume listening so we catch the next packets.
        self.radio.startListening()

    # =============================================================================
    def sendConfig(self, channelNo):
        url = BASE_API_URL + "channelSummary/" + str(channelNo)

        try:
            response = requests.get(url)

            # check if the response code is in the 200 range: 2xx
            responseCode = response.status_code - (response.status_code % 100)

            if responseCode != 200:
                print("No channel with the number", str(channelNo), "found!")
                print("Calibration could not be sent!")
                return

            
            channel = response.json() # ["channelSummary"]

            configPackage = Radio.PackageConfiguration(
                channel["sensorMeasureFrequencyMinutes"],
                channel["sensorTransmissionPowerLevelValue"],
                channel["sensorTriggerCalibration"],
            )

            print(
                "Measure Frequency: ",
                channel["sensorMeasureFrequencyMinutes"],
                "min",
            )

            print(
                "Transmission Power:",
                channel["sensorTransmissionPowerLevelValue"],
                "(" + str(channel["sensorTransmissionPowerLevel"]) + ")",
            )

            print("Trigger Calibrat.: ", channel["sensorTriggerCalibration"])

            byteArray = configPackage.toByteArray()

            self.radio.write(byteArray)

            print("Config was sent.")

            # remove the "trigger calibration" flag
            if channel["sensorTriggerCalibration"] == True:
                dataset_json = {"sensorTriggerCalibration": False}

                try:
                    url = BASE_API_URL + "channel/" + str(channelNo)
                    response = requests.put(url, json=dataset_json)

                    if response.ok == True:
                        print(
                            "Channel was updated (SensorTriggerCalibration = False)."
                        )
                    else:
                        print(
                            "There was an error updating the channel!",
                            response.reason,
                            response.status_code,
                        )

                except ConnectionError:
                    print("ERROR: The API is not reachable!", url)

        except ConnectionError:
            print("ERROR: The API is not reachable!", url)

    # =============================================================================
    # =============================================================================
    # =============================================================================
    class PackageConfiguration:
        packageType: np.uint8
        measureFrequency: np.uint16
        transmissionPowerLevel: np.uint8
        triggerCalibration: bool

        # =============================================================================
        def __init__(
            self, measureFrequency, transmissionPowerLevel, triggerCalibration
        ):
            self.packageType = DATATYPE_CONFIG
            self.measureFrequency = measureFrequency
            self.transmissionPowerLevel = transmissionPowerLevel
            self.triggerCalibration = triggerCalibration

        # =============================================================================
        def toByteArray(self):
            return pack(
                "<BHB?",
                self.packageType,
                self.measureFrequency,
                self.transmissionPowerLevel,
                self.triggerCalibration,
            )

    # =============================================================================
    # =============================================================================
    # =============================================================================
    class PackageSensorData:
        packageType: np.uint8
        moistureLevel: np.uint8
        batteryVoltage: float

        # =============================================================================
        def __init__(self, data: bytearray):
            # big endian for bytes
            packetBig = unpack(">BBf", data)

            # little endian for the float
            packetLittle = unpack("<BBf", data)

            self.packageType, self.moistureLevel, temp1 = packetBig
            temp2, temp3, self.batteryVoltage = packetLittle
