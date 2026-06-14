"""Tests for the silent-phase gate in actionEngine.handleActions.

The focus is the fail-closed behaviour: when the silent-phase status is unknown
(api.isInSilentPhase() returns None, e.g. the API is unreachable) the engine must
NOT water -- previously a None was treated as "not silent" and watering ran blind
on possibly-stale state.

These import only the core flat modules (the same way the service runs); the API
is a recorded fake so no HTTP or GPIO is touched.
"""

import types

import pytest

import actionEngine
from config import FlagHandler


class FakeController:
    '''Records run_pump calls; never touches hardware.'''

    def __init__(self):
        self.calls = []

    def run_pump(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()  # a non-None handle == "accepted"


@pytest.fixture(autouse=True)
def reset_flags():
    saved = list(FlagHandler.channelFlags)
    yield
    FlagHandler.channelFlags[:] = saved


def _set_only_first_flag():
    for i in range(len(FlagHandler.channelFlags)):
        FlagHandler.channelFlags[i] = (i == 0)


def test_unknown_silent_phase_skips_watering(monkeypatch):
    # None == "status unknown" -> fail closed, do not pump, keep the flag set.
    monkeypatch.setattr(actionEngine.api, "isInSilentPhase", lambda: None)
    controller = FakeController()
    _set_only_first_flag()

    actionEngine.handleActions(controller)

    assert controller.calls == []
    assert FlagHandler.channelFlags[0] is True  # flag kept for a later retry


def test_in_silent_phase_skips_watering(monkeypatch):
    monkeypatch.setattr(actionEngine.api, "isInSilentPhase", lambda: True)
    controller = FakeController()
    _set_only_first_flag()

    actionEngine.handleActions(controller)

    assert controller.calls == []


def test_not_silent_phase_evaluates_channels(monkeypatch):
    # False == "definitely not silent" -> proceed to evaluate channels. With a
    # summary that is above its trigger, no pump runs, but the channel WAS looked
    # up (proving None and False are handled differently).
    looked_up = []

    def fake_summary(channelNumber):
        looked_up.append(channelNumber)
        return {
            "enabled": True,
            "sensorData_lastMoisturePercent": 80,  # wet
            "actionTriggerPercent": 50,            # only water below this
            "pumpDurationSeconds": 10,
            "channelType": "valve",
        }

    monkeypatch.setattr(actionEngine.api, "isInSilentPhase", lambda: False)
    monkeypatch.setattr(actionEngine.api, "loadChannelSummary", fake_summary)
    controller = FakeController()
    _set_only_first_flag()

    actionEngine.handleActions(controller)

    assert looked_up == [1]
    assert controller.calls == []
