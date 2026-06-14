"""Unit tests for the pure wire-protocol layer (protocol.py).

protocol.py imports only the stdlib, so these run anywhere -- no pyrf24 / numpy
/ colorama / GPIO needed, the same philosophy as the pump-controller tests.

The cases below cover the protocol-hardening fixes: a low-battery reading is
parsed instead of dropped, malformed frames never raise, the wire layout is
pinned, and config bytes can be cached and answered from memory.
"""

import struct

import pytest

import protocol as p


PV = p.PROTOCOL_VERSION


def sensor_frame(version, ptype, moisture, battery):
    '''Build a sensor->master frame and zero-pad to PAYLOAD_SIZE, exactly as
    the radio delivers it.'''
    raw = struct.pack("<BBBf", version, ptype, moisture, battery)
    return raw.ljust(p.PAYLOAD_SIZE, b"\x00")


# 1 - normal sensor data parses; batteryAlert is False
def test_parse_normal_sensor_data():
    r = p.parse_sensor_reading(sensor_frame(PV, p.DATATYPE_SENSORDATA, 42, 3.7))
    assert r is not None
    assert r.moistureLevel == 42
    assert r.batteryVoltage == pytest.approx(3.7, abs=1e-6)
    assert r.batteryAlert is False


# 2 - a low-battery reading is STILL parsed and flagged (the P-01 regression):
#     previously this packet type matched no branch and the whole reading was
#     silently discarded.
def test_battery_alert_is_parsed_and_flagged():
    r = p.parse_sensor_reading(
        sensor_frame(PV, p.DATATYPE_SENSORDATA_BATTERYALERT, 10, 3.1))
    assert r is not None
    assert r.moistureLevel == 10
    assert r.batteryAlert is True


# 3 - malformed / short / empty / None frames return None, never raise
@pytest.mark.parametrize("bad", [None, b"", b"\x01", b"\x01\x00\x05", b"\x01\x00"])
def test_bad_payload_never_raises(bad):
    assert p.parse_sensor_reading(bad) is None
    # message_type tolerates the same garbage
    mt = p.message_type(bad)
    assert mt is None or isinstance(mt, int)


# 4 - a frame carrying a foreign protocol version is dropped, not mis-parsed
def test_foreign_version_dropped():
    assert p.parse_sensor_reading(sensor_frame(PV + 1, p.DATATYPE_SENSORDATA, 5, 3.0)) is None
    assert p.message_type(sensor_frame(PV + 1, p.DATATYPE_SENSORDATA, 5, 3.0)) is None


# 5 - message_type dispatches on the type byte for valid frames
def test_message_type_dispatch():
    assert p.message_type(sensor_frame(PV, p.DATATYPE_SENSORDATA, 5, 3.0)) == p.DATATYPE_SENSORDATA
    getconf = sensor_frame(PV, p.DATATYPE_CMD_GETCONFIG, 0, 0.0)
    assert p.message_type(getconf) == p.DATATYPE_CMD_GETCONFIG
    # a getconfig frame is not sensor data
    assert p.parse_sensor_reading(getconf) is None


# 6 - config payload round-trips and is the pinned wire size
def test_config_round_trip():
    payload = p.build_config_payload(60, 1, True)
    assert len(payload) == p.CONFIG_PAYLOAD_LEN == 6
    v = p.parse_config_payload(payload)
    assert v.measureFrequency == 60
    assert v.transmissionPowerLevel == 1
    assert v.triggerCalibration is True

    v2 = p.parse_config_payload(p.build_config_payload(15, 0, False))
    assert v2.measureFrequency == 15
    assert v2.triggerCalibration is False


# 7 - the on-air sizes match the packed firmware structs (Package=7, Config=6)
#     and fit inside the fixed payload size
def test_wire_sizes_match_firmware():
    assert p.SENSOR_PAYLOAD_LEN == 7
    assert p.CONFIG_PAYLOAD_LEN == 6
    assert p.PAYLOAD_SIZE >= p.SENSOR_PAYLOAD_LEN


# 8 - channel <-> pipe mapping reserves pipe 0 and validates bounds
def test_channel_pipe_mapping():
    # channels map 1:1 onto pipes 1..N; pipe 0 is never a channel
    for ch in range(1, 6):
        assert p.pipe_for_channel(ch) == ch
        assert p.channel_for_pipe(ch) == ch
    assert p.is_valid_channel(1, 5)
    assert p.is_valid_channel(5, 5)
    assert not p.is_valid_channel(0, 5)   # pipe 0 is reserved
    assert not p.is_valid_channel(6, 5)   # beyond the channel count


# 9 - the config cache answers from memory (hit) and reports misses
def test_config_cache():
    cache = p.ConfigCache()
    assert cache.get(3) is None
    assert not cache.has(3)

    payload = p.build_config_payload(30, 1, False)
    cache.put(3, payload)
    assert cache.has(3)
    assert cache.get(3) == payload
    # other channels remain a miss
    assert cache.get(4) is None
