import os
import sys
from datetime import datetime, timedelta

from pyrf24 import *

import requests
from requests.exceptions import ConnectionError, Timeout
from hardware import Pins, CHANNEL_COUNT

from config import *
from colorama import Fore

import protocol
from protocol import (
    DATATYPE_SENSORDATA,
    DATATYPE_SENSORDATA_BATTERYALERT,
    DATATYPE_CMD_GETCONFIG,
    DATATYPE_CONFIG,
    PAYLOAD_SIZE,
)

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

# Now you can import hardware
from globals.logger import Logger
from globals.secrets import TETHYS_API_KEY

# Sent on mutating API calls; the API gates POST/PUT/PATCH/DELETE behind this key.
_AUTH_HEADERS = {"X-API-Key": TETHYS_API_KEY}

# Timeout (seconds) on every HTTP call to the local API. Without it a hung API
# would block the radio loop indefinitely (the radio is not listening while we
# wait), stalling every sensor.
REQUEST_TIMEOUT = 5

# Fallback measurement interval (minutes) sent when a sensor asks before the
# config cache has been warmed. Matches the firmware default.
DEFAULT_MEASURE_FREQUENCY_MIN = 60


# =============================================================================
# =============================================================================
# =============================================================================
class Radio:

    # pipe 0 is the writing / auto-ACK address; pipes 1..CHANNEL_COUNT each
    # carry one sensor channel (see protocol.pipe_for_channel for why pipe 0 is
    # reserved). The nRF24L01 has 6 pipes total, so with pipe 0 reserved this
    # tops out at 5 sensor channels.
    _pipeAddresses = [
        0x5232443230,
        0x5232443231,
        0x5232443232,
        0x5232443233,
        0x5232443234,
        0x5232443235,
    ]

    _logger = Logger(Fore.GREEN)

    # =============================================================================
    def __init__(self):

        self.radio = RF24(Pins.CE, Pins.CSN)

        # Last-known config per channel, kept warm out-of-band so a GETCONFIG
        # can be answered instantly instead of via a blocking HTTP GET inside
        # the sensor's short listen window.
        self._configCache = protocol.ConfigCache()

    # =============================================================================
    def initializeRadio(self):

        self.radio.begin()

        self.radio.setAddressWidth(5)
        self.radio.setAutoAck(True)
        self.radio.setCRCLength(RF24_CRC_8)
        self.radio.setPALevel(RF24_PA_LOW)
        self.radio.setDataRate(RF24_250KBPS)

        # Fixed payload size on both ends: framing is explicit and we never
        # depend on getDynamicPayloadSize() (undefined while dynamic payloads
        # are disabled, and can make the radio flush the RX FIFO).
        self.radio.setPayloadSize(PAYLOAD_SIZE)

        # Deterministic auto-ACK retransmission: 15 retries, 1500us apart.
        self.radio.setRetries(5, 15)

        self.radio.printDetails()
        print("===================================================")

        # Writing pipe (master -> sensor) on the reserved pipe-0 address.
        self.radio.openWritingPipe(self._pipeAddresses[0])

        # Each sensor channel maps 1:1 onto a reading pipe; pipe 0 stays free
        # for the ACK/writing address. This caps the link at CHANNEL_COUNT
        # sensors (6 hardware pipes - 1 reserved).
        for channel in range(1, CHANNEL_COUNT + 1):
            self.radio.openReadingPipe(
                protocol.pipe_for_channel(channel),
                self._pipeAddresses[channel])

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

        if not self.radio.available():
            return

        # Drain the whole RX FIFO first (up to 3 frames can queue, each from a
        # potentially different pipe), then process them. The old code kept
        # only the last frame and silently dropped the rest.
        frames = []
        while self.radio.available():
            hasData, pipeNo = self.radio.available_pipe()
            if not hasData:
                break
            payload = self.radio.read(PAYLOAD_SIZE)
            frames.append((pipeNo, payload))

        for pipeNo, payload in frames:
            channelNo = protocol.channel_for_pipe(pipeNo)

            self._logger.log(f'Incoming from Pipe: {pipeNo} (channel {channelNo})')
            self._logger.increaseIndent()

            if not protocol.is_valid_channel(channelNo, CHANNEL_COUNT):
                self._logger.log("Invalid pipe number!")
                self._logger.decreaseIndent()
                continue

            self.handlePayload(channelNo, payload)
            self._logger.decreaseIndent()

    # =============================================================================
    def handlePayload(self, channelNo, payload):
        # stop listening so we can send any answer; always resume afterwards
        self.radio.stopListening()

        try:
            messageType = protocol.message_type(payload)

            if messageType is None:
                self._logger.log("Dropping malformed / foreign-version packet.")
                return

            # the sensor requested the configuration
            if messageType == DATATYPE_CMD_GETCONFIG:
                self._logger.log("Config was requested.")
                self.sendConfig(channelNo)

            # a moisture reading -- normal OR low-battery. Both must be saved;
            # previously a low-battery packet matched neither branch and the
            # whole reading was silently discarded.
            elif messageType in (DATATYPE_SENSORDATA,
                                 DATATYPE_SENSORDATA_BATTERYALERT):
                self.handleSensorData(channelNo, payload)

            else:
                self._logger.log(f"Ignoring unsupported message type {messageType}.")

        finally:
            # Now, resume listening so we catch the next packets.
            self.radio.startListening()

    # =============================================================================
    def handleSensorData(self, channelNo, payload):

        reading = protocol.parse_sensor_reading(payload)
        if reading is None:
            self._logger.log("Sensor-data packet failed validation; dropped.")
            return

        self._logger.log("Sensordata received.")

        batteryVoltageformatted = '{0:.2f}'.format(reading.batteryVoltage)

        self._logger.increaseIndent()
        self._logger.log(f'Moisture:        {reading.moistureLevel} %')
        self._logger.log(f'Battery Voltage: {batteryVoltageformatted} V')
        if reading.batteryAlert:
            self._logger.log('Battery LOW alert flagged by sensor!')
        self._logger.decreaseIndent()

        if not protocol.is_valid_channel(channelNo, CHANNEL_COUNT):
            self._logger.log(f"Ignoring data for unknown channel {channelNo}")
            return

        # NOTE: the low-battery flag is not yet persisted (SensorData has no
        # such column); the saved voltage already carries the information and
        # the alert is logged. A dedicated battery-alert field is tracked as a
        # backend follow-up in TODO.md.
        dataset_json = {
            "channel": channelNo,
            "batteryVoltage": reading.batteryVoltage,
            "moisturePercent": reading.moistureLevel,
        }

        url = BASE_API_URL + "sensorData/"

        try:
            response = requests.post(
                url, json=dataset_json, headers=_AUTH_HEADERS, timeout=REQUEST_TIMEOUT)

            # check if the response code is in the 200 range: 2xx
            responseCode = response.status_code - (response.status_code % 100)

            if responseCode == 200:
                self._logger.log("Data was succesfully saved to the API.")
                FlagHandler().channelFlags[channelNo - 1] = True
            else:
                self._logger.log("There was an error saving the data: ", response.reason)

        except (ConnectionError, Timeout):
            self._logger.log(f'ERROR: The API is not reachable! {url}')

    # =============================================================================
    def refreshConfigCache(self):
        '''Pull every channel's current config from the API and cache the wire
        bytes. Called from the core loop OUTSIDE the radio response window, so a
        sensor's GETCONFIG can be answered instantly from memory. Best-effort:
        a failed fetch leaves the previous cache entry intact.'''

        for channel in range(1, CHANNEL_COUNT + 1):
            url = BASE_API_URL + "channelSummary/" + str(channel)

            try:
                response = requests.get(url, headers=_AUTH_HEADERS, timeout=REQUEST_TIMEOUT)
            except (ConnectionError, Timeout):
                self._logger.log(f'Config refresh: API not reachable ({url}).')
                continue

            if not response.ok:
                continue

            data = response.json()
            payload = protocol.build_config_payload(
                data["sensorMeasureFrequencyMinutes"],
                data["sensorTransmissionPowerLevelValue"],
                data["sensorTriggerCalibration"],
            )
            self._configCache.put(channel, payload)

    # =============================================================================
    def sendConfig(self, channelNo):

        payload = self._configCache.get(channelNo)

        if payload is None:
            # Cache miss: still answer within the sensor's listen window with a
            # safe default, and let the next refresh warm the cache.
            payload = protocol.build_config_payload(
                DEFAULT_MEASURE_FREQUENCY_MIN, int(RF24_PA_LOW), False)
            self._logger.log(
                f"Config cache miss for channel {channelNo}; sent safe default.")

        # The write returns True only if the node hardware-ACKed the frame, i.e.
        # actually received the config. Capture that: a calibration trigger is a
        # one-shot, so we must NOT clear it unless we know it was delivered --
        # otherwise an unacked reply (the node's 500ms listen window closed, RF
        # glitch, ...) silently consumes the request and calibration never runs.
        delivered = bool(self.radio.write(payload))
        self._logger.log(
            "Config was sent." if delivered
            else "Config send was NOT acknowledged (will retry next handshake).")

        # If this config carried a calibration trigger AND it was delivered, clear
        # it now -- this is out of the sensor's listen window, so the blocking HTTP
        # PUT is fine. If it was not delivered, leave the flag set so the next
        # handshake re-delivers it.
        values = protocol.parse_config_payload(payload)
        if delivered and values is not None and values.triggerCalibration:
            self.clearCalibrationFlag(channelNo, values)

    # =============================================================================
    def clearCalibrationFlag(self, channelNo, values):
        url = BASE_API_URL + "channel/" + str(channelNo)

        try:
            response = requests.put(
                url, json={"sensorTriggerCalibration": False},
                headers=_AUTH_HEADERS, timeout=REQUEST_TIMEOUT)

            if response.ok:
                self._logger.log('Channel was updated (SensorTriggerCalibration = False).')
                # reflect the cleared flag in the cache so we don't re-trigger
                # calibration before the next refresh
                self._configCache.put(channelNo, protocol.build_config_payload(
                    values.measureFrequency, values.transmissionPowerLevel, False))
            else:
                self._logger.log(
                    f'There was an error updating the channel! {response.reason} {response.status_code}')

        except (ConnectionError, Timeout):
            self._logger.log(f'ERROR: The API is not reachable! {url}')
