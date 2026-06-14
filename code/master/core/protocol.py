"""
Wire protocol for the Tethys nRF24 link (master side).

This module is intentionally free of hardware / 3rd-party imports (only the
stdlib ``struct``) so the framing rules can be unit-tested on any machine, the
same way the pump-control logic is exercised through a fake GPIO seam. The
radio driver (``radio.py``) does the I/O; everything about how bytes are laid
out, validated and dispatched lives here.

Both ends speak a fixed-size, *versioned* binary format. Every on-air payload
is exactly ``PAYLOAD_SIZE`` bytes (the radio zero-pads short frames). The first
byte is the protocol version and the second byte is the message type, so a
receiver can validate the version and dispatch on the type *before* trusting
the rest of the frame.

Wire layout (little-endian, packed -- MUST match
``code/sensor/include/wpw_RXTX.h``):

  Sensor -> Master (DATATYPE_SENSORDATA / _BATTERYALERT / _CMD_GETCONFIG /
                    _CMD_GETCONFIG_PERIODIC):
      uint8  protocolVersion
      uint8  packageType
      uint8  moistureLevel        (0-100)
      float  batteryVoltage       (4 bytes, IEEE-754)
    => 7 payload bytes

  Master -> Sensor (DATATYPE_CONFIG):
      uint8  protocolVersion
      uint8  packageType
      uint16 measureFrequency     (minutes)
      uint8  transmissionPowerLevel
      bool   triggerCalibration
    => 6 payload bytes
"""

import struct
from collections import namedtuple


# Bump whenever the wire layout changes. Both firmware and master must agree;
# a frame whose first byte != PROTOCOL_VERSION is dropped instead of mis-parsed.
PROTOCOL_VERSION = 1

# Fixed on-air payload size in bytes. Both ends call ``setPayloadSize`` with
# this value; frames shorter than this are zero-padded by the radio. Must be
# >= the largest message (sensor data = 7 bytes); a byte of headroom is kept.
PAYLOAD_SIZE = 8

DATATYPE_SENSORDATA = 0
DATATYPE_SENSORDATA_BATTERYALERT = 1
DATATYPE_CMD_CALIBRATE = 5          # master -> sensor (reserved, unused today)
DATATYPE_CMD_GETCONFIG = 6          # sensor -> master
DATATYPE_CONFIG = 7                 # master -> sensor
DATATYPE_CMD_GETCONFIG_PERIODIC = 8  # sensor -> master (settings-only pull)

_SENSOR_STRUCT = struct.Struct("<BBBf")     # version, type, moisture, battery
_CONFIG_STRUCT = struct.Struct("<BBHB?")    # version, type, freq, power, calib

SENSOR_PAYLOAD_LEN = _SENSOR_STRUCT.size    # 7
CONFIG_PAYLOAD_LEN = _CONFIG_STRUCT.size    # 6

SensorReading = namedtuple(
    "SensorReading", "moistureLevel batteryVoltage batteryAlert")
ConfigValues = namedtuple(
    "ConfigValues", "measureFrequency transmissionPowerLevel triggerCalibration")


# =============================================================================
def message_type(payload):
    """Return the message-type byte, or ``None`` if the frame is too short or
    carries a mismatched protocol version. Never raises on malformed input, so
    it is safe to call on whatever bytes the radio hands us."""
    if payload is None or len(payload) < 2:
        return None
    if payload[0] != PROTOCOL_VERSION:
        return None
    return payload[1]


# =============================================================================
def parse_sensor_reading(payload):
    """Parse a sensor-data frame (type 0 or 1) into a :class:`SensorReading`,
    or return ``None`` for a malformed / wrong-version / non-sensor frame.

    ``batteryAlert`` is ``True`` for ``DATATYPE_SENSORDATA_BATTERYALERT`` -- the
    whole point of routing that type here is that a low battery must no longer
    cause the entire reading to be silently discarded."""
    if payload is None or len(payload) < SENSOR_PAYLOAD_LEN:
        return None
    version, ptype, moisture, battery = _SENSOR_STRUCT.unpack_from(payload)
    if version != PROTOCOL_VERSION:
        return None
    if ptype not in (DATATYPE_SENSORDATA, DATATYPE_SENSORDATA_BATTERYALERT):
        return None
    return SensorReading(
        moistureLevel=moisture,
        batteryVoltage=battery,
        batteryAlert=(ptype == DATATYPE_SENSORDATA_BATTERYALERT),
    )


# =============================================================================
def build_config_payload(measureFrequency, transmissionPowerLevel,
                         triggerCalibration):
    """Serialise a ``DATATYPE_CONFIG`` frame to bytes, ready for ``radio.write``."""
    return _CONFIG_STRUCT.pack(
        PROTOCOL_VERSION,
        DATATYPE_CONFIG,
        int(measureFrequency) & 0xFFFF,
        int(transmissionPowerLevel) & 0xFF,
        bool(triggerCalibration),
    )


# =============================================================================
def parse_config_payload(payload):
    """Inverse of :func:`build_config_payload` (used by tests / a firmware
    emulation harness). Returns :class:`ConfigValues` or ``None``."""
    if payload is None or len(payload) < CONFIG_PAYLOAD_LEN:
        return None
    version, ptype, freq, power, calib = _CONFIG_STRUCT.unpack_from(payload)
    if version != PROTOCOL_VERSION or ptype != DATATYPE_CONFIG:
        return None
    return ConfigValues(
        measureFrequency=freq,
        transmissionPowerLevel=power,
        triggerCalibration=calib,
    )


# =============================================================================
def is_valid_channel(channel, channel_count):
    """A channel exists iff 1 <= channel <= channel_count."""
    return isinstance(channel, int) and 1 <= channel <= channel_count


# =============================================================================
def pipe_for_channel(channel):
    """Hardware reading-pipe index for a sensor channel.

    Channels map 1:1 onto reading pipes 1..N. Pipe 0 is deliberately left for
    the auto-ACK / writing address: on the nRF24 the radio reuses pipe 0 to
    receive ACKs whenever it transmits, so binding a sensor to pipe 0 makes
    that sensor's reception unreliable. Reserving it caps the link at 5 sensors
    (6 pipes - 1), which matches the hardware channel count."""
    return channel


def channel_for_pipe(pipe):
    """Inverse of :func:`pipe_for_channel` -- the channel a given reading pipe
    carries."""
    return pipe


# =============================================================================
class ConfigCache:
    """Last-known config payload per channel.

    A sensor only listens for a config reply for a few hundred milliseconds
    after asking. Fetching that config from the HTTP API *inside* that window
    is the race that makes the boot handshake fail (and triggers the firmware's
    retry storm). The radio keeps this cache warm out-of-band (see
    ``Radio.refreshConfigCache``) so a ``GETCONFIG`` can be answered instantly
    from memory."""

    def __init__(self):
        self._payloads = {}

    def put(self, channel, payload_bytes):
        self._payloads[channel] = payload_bytes

    def get(self, channel):
        """Cached config bytes for ``channel`` or ``None`` on a miss."""
        return self._payloads.get(channel)

    def has(self, channel):
        return channel in self._payloads
