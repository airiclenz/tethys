"""Unit tests for Radio.saveFirmwareVersion (boot-time version persistence).

The master records the firmware version a sensor reports on its boot-time
GETCONFIG handshake. It must:
  * parse the version out of the request frame and PUT it to the channel,
  * skip the PUT when the version is unchanged -- a node stuck in a reboot loop
    must not re-write the same value (and trigger a web refresh) every boot,
  * only remember a version once the API actually accepted it, so a failed write
    is retried on the next boot.

Like the other core tests this runs without a Pi / pyrf24 radio / live API:
Radio is built via __new__ (skipping the RF24 constructor) and the HTTP layer is
faked, the same seam philosophy as the sendConfig and protocol tests.
"""

import struct

import protocol
import radio as radio_module
from radio import Radio


class FakeResponse:
    def __init__(self, ok=True, reason="OK", status_code=200):
        self.ok = ok
        self.reason = reason
        self.status_code = status_code


class FakeRequests:
    '''Records PUT calls and returns a configurable response (stands in for the
    module-level ``requests`` in radio.py).'''

    def __init__(self, ok=True):
        self._ok = ok
        self.puts = []

    def put(self, url, json=None, headers=None, timeout=None):
        self.puts.append({"url": url, "json": json})
        return FakeResponse(ok=self._ok)


class QuietLogger:
    def log(self, *_args, **_kwargs):
        pass

    def increaseIndent(self):
        pass

    def decreaseIndent(self):
        pass


def _make_radio():
    obj = Radio.__new__(Radio)
    obj._logger = QuietLogger()
    obj._lastFirmwareVersion = {}
    return obj


def boot_frame(major, minor, build, ptype=protocol.DATATYPE_CMD_GETCONFIG):
    '''A config-request frame carrying a firmware version, zero-padded to
    PAYLOAD_SIZE the way the radio delivers it.'''
    raw = struct.pack(
        "<BBBBB", protocol.PROTOCOL_VERSION, ptype, major, minor, build)
    return raw.ljust(protocol.PAYLOAD_SIZE, b"\x00")


# 1 - a readable version is PUT to the channel as "major.minor.build"
def test_saves_reported_version(monkeypatch):
    fake = FakeRequests(ok=True)
    monkeypatch.setattr(radio_module, "requests", fake)
    obj = _make_radio()

    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))

    assert len(fake.puts) == 1
    assert fake.puts[0]["json"] == {"sensorFirmwareVersion": "3.1.24"}
    assert fake.puts[0]["url"].endswith("channel/1")
    assert obj._lastFirmwareVersion[1] == "3.1.24"


# 2 - an unchanged version is not re-PUT on the next boot
def test_unchanged_version_not_rewritten(monkeypatch):
    fake = FakeRequests(ok=True)
    monkeypatch.setattr(radio_module, "requests", fake)
    obj = _make_radio()

    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))
    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))

    assert len(fake.puts) == 1


# 3 - a changed version IS written (e.g. after re-flashing a sensor)
def test_changed_version_is_rewritten(monkeypatch):
    fake = FakeRequests(ok=True)
    monkeypatch.setattr(radio_module, "requests", fake)
    obj = _make_radio()

    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))
    obj.saveFirmwareVersion(1, boot_frame(3, 2, 0))

    assert len(fake.puts) == 2
    assert fake.puts[-1]["json"] == {"sensorFirmwareVersion": "3.2.0"}
    assert obj._lastFirmwareVersion[1] == "3.2.0"


# 4 - a failed PUT is not remembered, so the next boot retries the write
def test_failed_put_not_remembered(monkeypatch):
    fake = FakeRequests(ok=False)
    monkeypatch.setattr(radio_module, "requests", fake)
    obj = _make_radio()

    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))
    assert 1 not in obj._lastFirmwareVersion

    obj.saveFirmwareVersion(1, boot_frame(3, 1, 24))
    assert len(fake.puts) == 2


# 5 - an unreadable / malformed frame is ignored (no PUT, never raises)
def test_unreadable_frame_ignored(monkeypatch):
    fake = FakeRequests(ok=True)
    monkeypatch.setattr(radio_module, "requests", fake)
    obj = _make_radio()

    obj.saveFirmwareVersion(1, b"")

    assert fake.puts == []
