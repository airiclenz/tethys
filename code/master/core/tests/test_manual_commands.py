"""Tests for manualCommands.drain -- the core side of the manual-command queue.

The web UI enqueues activate/deactivate requests; the core runs them through the
SAME pump controller as automatic watering. The point of the change is that the
one-channel power limit ("max one channel + pump at a time") now holds for manual
taps too: an activate that arrives while another channel is running is rejected,
not run. These tests exercise a real PumpController (with a fake GPIO adapter and
non-running timers) and a recorded fake API, so no HTTP or hardware is touched.
"""

import pytest

import manualCommands
from gpioAdapter import FakeGpioAdapter
from hardware import Pins
from pumpController import PumpController

from tests._helpers import FakeTimer


def make_pc(max_concurrent=1):
    '''Controller wired to a fake adapter and non-running timers.'''
    fake = FakeGpioAdapter()
    timers = []

    def factory(interval, function, args=None, kwargs=None):
        timer = FakeTimer(interval, function, args, kwargs)
        timers.append(timer)
        return timer

    pc = PumpController(
        fake, Pins, max_concurrent=max_concurrent, timer_factory=factory,
    )
    return pc, fake, timers


class FakeApi:
    '''Stands in for apiInterface: serves a fixed pending list and records every
    reported outcome as (commandId, status).'''

    def __init__(self, pending):
        self._pending = pending
        self.results = []

    def fetchPendingManualCommands(self):
        return self._pending

    def reportManualCommandResult(self, commandId, resultStatus, message=""):
        self.results.append((commandId, resultStatus))


def _command(commandId, channel, action="activate", channelType="valve", ageSeconds=1):
    return {
        "id": commandId,
        "channel": channel,
        "channelType": channelType,
        "action": action,
        "ageSeconds": ageSeconds,
    }


@pytest.fixture
def patch_api(monkeypatch):
    def _install(pending):
        fake = FakeApi(pending)
        monkeypatch.setattr(manualCommands, "api", fake)
        return fake
    return _install


# activate on a free controller is accepted and energises the channel
def test_activate_on_free_controller_is_accepted(patch_api):
    fake_api = patch_api([_command(1, 1)])
    pc, _gpio, _timers = make_pc()

    manualCommands.drain(pc)

    assert fake_api.results == [(1, "accepted")]
    assert pc.is_running(1)


# the power limit: a manual activate while another channel runs is rejected
def test_activate_while_busy_is_rejected(patch_api):
    fake_api = patch_api([_command(2, 2)])
    pc, _gpio, _timers = make_pc(max_concurrent=1)
    pc.run_pump(1, 10, "valve")  # channel 1 already running

    manualCommands.drain(pc)

    assert fake_api.results == [(2, "rejected")]
    assert not pc.is_running(2)


# a stale activate is ignored (expired), never energising the channel
def test_stale_activate_is_expired(patch_api):
    age = manualCommands.MANUAL_COMMAND_MAX_AGE_SECONDS + 1
    fake_api = patch_api([_command(3, 3, ageSeconds=age)])
    pc, _gpio, _timers = make_pc()

    manualCommands.drain(pc)

    assert fake_api.results == [(3, "expired")]
    assert not pc.is_running(3)


# deactivate drives the channel off and reports done
def test_deactivate_reports_done(patch_api):
    fake_api = patch_api([_command(4, 1, action="deactivate")])
    pc, _gpio, _timers = make_pc()
    pc.run_pump(1, 10, "valve")  # running, so there is something to turn off

    manualCommands.drain(pc)

    assert fake_api.results == [(4, "done")]
    assert not pc.is_running(1)


# an unknown action is reported as failed, never silently dropped
def test_unknown_action_is_failed(patch_api):
    fake_api = patch_api([_command(5, 1, action="wiggle")])
    pc, _gpio, _timers = make_pc()

    manualCommands.drain(pc)

    assert fake_api.results == [(5, "failed")]
