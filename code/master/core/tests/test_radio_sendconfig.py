"""Unit tests for Radio.sendConfig calibration-flag delivery semantics.

The calibrate trigger is a one-shot the master clears after sending it to the
sensor. It must only be cleared when the config frame was actually delivered
(hardware-ACKed). Otherwise a missed reply -- the sensor's ~500ms listen window
closes before the master answers, an RF glitch, etc. -- silently consumes the
calibration request and calibration never runs even though the user set the
flag and rebooted the node.

Like the other core tests this runs without a Pi / pyrf24 radio: Radio is built
via __new__ (skipping the RF24 constructor) and its collaborators are faked,
the same seam philosophy as the pump-controller and protocol tests.
"""

import protocol
from radio import Radio


class FakeRadio:
    '''Minimal stand-in for the pyrf24 RF24 object: records each write and
    returns a configurable ACK result (mirrors FakeTimer in _helpers.py).'''

    def __init__(self, write_result):
        self._write_result = write_result
        self.written = []

    def write(self, payload):
        self.written.append(payload)
        return self._write_result


class QuietLogger:
    '''Swallow log output so the tests stay silent.'''

    def log(self, *_args, **_kwargs):
        pass

    def increaseIndent(self):
        pass

    def decreaseIndent(self):
        pass


def _make_radio(write_result, cached_payload, channel=1):
    '''A Radio with hardware/HTTP collaborators faked and one cached config.'''
    obj = Radio.__new__(Radio)
    obj.radio = FakeRadio(write_result)
    obj._configCache = protocol.ConfigCache()
    obj._configCache.put(channel, cached_payload)
    obj._logger = QuietLogger()

    cleared = []
    obj.clearCalibrationFlag = lambda channelNo, values: cleared.append(channelNo)
    return obj, cleared


CALIB_PAYLOAD = protocol.build_config_payload(60, 0, True)


# 1 - send not acknowledged -> flag preserved (re-delivered next handshake)
def test_calibration_flag_not_cleared_when_send_unacked():
    obj, cleared = _make_radio(write_result=False, cached_payload=CALIB_PAYLOAD)

    obj.sendConfig(1)

    assert cleared == []
    # the cached config still carries the calibration trigger for next time
    still = protocol.parse_config_payload(obj._configCache.get(1))
    assert still.triggerCalibration is True


# 2 - send acknowledged -> one-shot flag cleared exactly once
def test_calibration_flag_cleared_when_send_acked():
    obj, cleared = _make_radio(write_result=True, cached_payload=CALIB_PAYLOAD)

    obj.sendConfig(1)

    assert cleared == [1]


# 3 - no calibration trigger in the config -> never attempt to clear
def test_no_clear_attempt_when_no_calibration_trigger():
    payload = protocol.build_config_payload(60, 0, False)
    obj, cleared = _make_radio(write_result=True, cached_payload=payload)

    obj.sendConfig(1)

    assert cleared == []
