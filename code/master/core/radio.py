import os
import sys
import struct
from datetime import datetime, timedelta
import numpy as np

from pyrf24 import *

import requests
from requests.exceptions import ConnectionError
from hardware import Pins

from config import *
from colorama import Fore

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

# Now you can import hardware
from globals.logger import Logger


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
        0x5232443236,
    ]

    _logger = Logger(Fore.GREEN)

    # =============================================================================
    def __init__(self):
        
        self.radio = RF24(Pins.CE, Pins.CSN)


    # =============================================================================
    def initializeRadio(self):
        
        self.radio.begin()
        
        self.radio.setAddressWidth(5)
        self.radio.setAutoAck(True)
        self.radio.setCRCLength(RF24_CRC_8)
        self.radio.setPALevel(RF24_PA_LOW)
        self.radio.setDataRate(RF24_250KBPS)
        

        self.radio.printDetails()
        print("===================================================")


        # setting up the reading- and writing pites
        self.radio.openWritingPipe(self._pipeAddresses[0])

        self.radio.openReadingPipe(0, self._pipeAddresses[1])
        self.radio.openReadingPipe(1, self._pipeAddresses[2])
        self.radio.openReadingPipe(2, self._pipeAddresses[3])
        self.radio.openReadingPipe(3, self._pipeAddresses[4])
        self.radio.openReadingPipe(4, self._pipeAddresses[5])
        self.radio.openReadingPipe(5, self._pipeAddresses[6])

        self.radio.startListening()


    # =============================================================================
    def setupInterrupt(self):

        pass

        '''
        # interrupt alternative with gpiod:

        try:  # try RPi5 gpio chip first
            chip_path = "/dev/gpiochip4"
            chip = gpiod.Chip(chip_path)
        except FileNotFoundError:  # fall back to gpio chip for RPi4 or older
            chip_path = "/dev/gpiochip0"
            chip = gpiod.Chip(chip_path)
        finally:
            print(__file__)  # print example name
            # print gpio chip info
            info = chip.get_info()
            print(f"Using {info.name} [{info.label}]")
        
        self.IRQ_Line = gpiod.request_lines(
            path=chip_path,
            consumer="checkRadioInbox",  # optional
            config={Pins.IRQ: gpiod.LineSettings(edge_detection=Edge.FALLING)},
        )
        '''


        '''
        # interrupt alternative with RPi.GPIO

        # set up callback for irq pin
        GPIO.setmode(GPIO.BCM)
        #GPIO.setup(Pins.IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(Pins.IRQ, GPIO.IN)
        GPIO.add_event_detect(Pins.IRQ, GPIO.FALLING, callback=self.checkRadioInbox)
        '''


    # =============================================================================
    def handleRadioEvents(self, timeOutInSec: int):

        endtime = datetime.now() + timedelta(seconds=timeOutInSec)
        
        while True:
            self.checkRadioInbox()

            if datetime.now() > endtime:
                return


    # =============================================================================
    def checkRadioInbox(self):

        if self.radio.available() == True:
            
            pipeNo = self.radio.available_pipe()[1] + 1

            self._logger.log(f'Incoming from Pipe: {pipeNo}')
            self._logger.increaseIndent()

            if pipeNo < 1 or pipeNo > 6:
                self._logger.log("Invalid pipe number!")
                self._logger.decreaseIndent()
                return

            while self.radio.available():
                len = self.radio.getDynamicPayloadSize()

                payload = self.radio.read(len)

            # handle what we received
            self.handlePayload(pipeNo, payload)
            self._logger.decreaseIndent()


    # =============================================================================
    def handlePayload(self, channelNo, payload):
        # stop listening so we can send the appropriate answer
        self.radio.stopListening()

        command = payload[0]

        # the sensor requested the configuration
        if command == DATATYPE_CMD_GETCONFIG:
            self._logger.log("Config was requested.")
            self.sendConfig(channelNo)

        elif command == DATATYPE_SENSORDATA:
            self._logger.log("Sensordata received.")

            package = Radio.PackageSensorData(payload)
            
            batteryVoltageformatted = '{0:.2f}'.format(package.batteryVoltage)

            self._logger.increaseIndent()
            self._logger.log(f'Moisture:        {package.moistureLevel} %')
            self._logger.log(f'Battery Voltage: {batteryVoltageformatted} V')
            self._logger.decreaseIndent()

            dataset_json = {
                "channel": channelNo,
                "batteryVoltage": package.batteryVoltage,
                "moisturePercent": package.moistureLevel,
            }

            url = BASE_API_URL + "sensorData/"

            try:
                response = requests.post(url, json=dataset_json)

                # check if the response code is in the 200 range: 2xx
                responseCode = response.status_code - (response.status_code % 100)

                if responseCode == 200:
                    self._logger.log("Data was succesfully saved to the API.")

                    FlagHandler().channelFlags[channelNo - 1] = True

                else:
                    self._logger.log("There was an error saving the data: ", response.reason)

            except ConnectionError:
                self._logger.log(f'ERROR: The API is not reachable! {url}')

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
                self._logger.log("No channel with the number", str(channelNo), "found!")
                self._logger.log("Calibration could not be sent!")
                return

            
            channel = response.json() # ["channelSummary"]

            configPackage = Radio.PackageConfiguration(
                channel["sensorMeasureFrequencyMinutes"],
                channel["sensorTransmissionPowerLevelValue"],
                channel["sensorTriggerCalibration"],
            )

            self._logger.increaseIndent()
            self._logger.log(f'Measure Frequency:  {channel["sensorMeasureFrequencyMinutes"]} min')
            self._logger.log(f'Transmission Power: {channel["sensorTransmissionPowerLevelValue"]} ( {str(channel["sensorTransmissionPowerLevel"])} )')
            self._logger.log(f'Trigger Calibrat.:  {channel["sensorTriggerCalibration"]}')
            self._logger.decreaseIndent()

            byteArray = configPackage.toByteArray()

            self.radio.write(byteArray)

            self._logger.log("Config was sent.")

            # remove the "trigger calibration" flag
            if channel["sensorTriggerCalibration"] == True:
                dataset_json = {"sensorTriggerCalibration": False}

                try:
                    url = BASE_API_URL + "channel/" + str(channelNo)
                    response = requests.put(url, json=dataset_json)

                    if response.ok == True:
                        self._logger.log('Channel was updated (SensorTriggerCalibration = False).')
                    else:
                        self._logger.log(f'There was an error updating the channel! {response.reason} {response.status_code}')

                except ConnectionError:
                    self._logger.log(f'ERROR: The API is not reachable! {url}')

        except ConnectionError:
            self._logger.log(f'ERROR: The API is not reachable! {url}')

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
            return struct.pack(
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
            
            unpackedUInts = struct.unpack('BB', data[:2])
            self.packageType = unpackedUInts[0]
            self.moistureLevel = unpackedUInts[1]

            self.batteryVoltage = struct.unpack('f', data[2:6])[0]



