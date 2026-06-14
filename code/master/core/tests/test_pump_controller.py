import pytest

from gpioAdapter import FakeGpioAdapter
from hardware import Pins, CHANNEL_COUNT
from pumpController import PumpController, PumpError, MAX_PUMP_SECONDS

from tests._helpers import FakeTimer

CH1 = Pins.CHANNELS[0]   # 16
CH2 = Pins.CHANNELS[1]   # 19
PUMP = Pins.PUMP         # 6


def make_pc(max_concurrent=1):
    '''Controller wired to a fake adapter and non-running timers. Returns
    (controller, fake_adapter, list_of_created_timers).'''
    fake = FakeGpioAdapter()
    timers = []

    def factory(interval, function, args=None, kwargs=None):
        t = FakeTimer(interval, function, args, kwargs)
        timers.append(t)
        return t

    pc = PumpController(
        fake, Pins, max_concurrent=max_concurrent, timer_factory=factory,
    )
    return pc, fake, timers


# 1 - the unbounded DB duration is clamped to the hard ceiling
def test_run_pump_clamps_duration():
    pc, fake, timers = make_pc()
    pc.run_pump(1, 99999, "pump")
    assert timers[0].interval == MAX_PUMP_SECONDS


# 2 - a failed ON write never reports success and best-effort drives the line LOW
def test_failed_on_write_raises_and_attempts_off():
    pc, fake, timers = make_pc()
    fake.fail_high = {CH1}                      # cannot energise, but LOW works
    with pytest.raises(PumpError):
        pc.run_pump(1, 10, "pump")
    assert (CH1, 0) in fake.writes             # try/finally best-effort off
    assert not pc.is_running(1)                # not treated as running
    assert timers == []                        # no auto-off timer scheduled


# 3 - the auto-off timer guarantees the pump switches off
def test_auto_off_timer_switches_pump_off():
    pc, fake, timers = make_pc()
    on_complete = []
    pc.run_pump(2, 10, "pump", on_complete=lambda s, e: on_complete.append((s, e)))
    assert pc.is_running(2)
    timers[0].fire()
    assert fake.writes[-1] == (CH2, 0)
    assert not pc.is_running(2)
    assert len(on_complete) == 1               # DB-log callback fired once
    start, end = on_complete[0]
    assert end >= start


# 4 - valve drives channel + shared PUMP pin; plain pump drives only its channel
def test_write_sequences_per_channel_type():
    pc, fake, timers = make_pc()
    pc.run_pump(1, 10, "valve")
    timers[0].fire()
    assert fake.writes == [(CH1, 1), (PUMP, 1), (CH1, 0), (PUMP, 0)]

    pc2, fake2, timers2 = make_pc()
    pc2.run_pump(2, 10, "pump")
    timers2[0].fire()
    assert fake2.writes == [(CH2, 1), (CH2, 0)]


# 5 - deactivate returns the real write result, it never lies
def test_deactivate_reports_real_failure():
    pc, fake, timers = make_pc()
    fake.fail_pins = {CH1}
    assert pc.deactivate(1, "pump") is False
    fake.fail_pins = set()
    assert pc.deactivate(1, "pump") is True


# 6 - out-of-range channels raise ValueError, never an IndexError
def test_channel_bounds():
    pc, fake, timers = make_pc()
    with pytest.raises(ValueError):
        pc.run_pump(CHANNEL_COUNT + 1, 10, "pump")
    with pytest.raises(ValueError):
        pc.run_pump(0, 10, "pump")


# 7 - the shared PUMP pin is ref-counted across overlapping valve channels
def test_pump_pin_refcounted_for_overlapping_valves():
    pc, fake, timers = make_pc(max_concurrent=5)
    pc.run_pump(1, 10, "valve")
    pc.run_pump(2, 10, "valve")
    fake.writes.clear()

    pc.deactivate(1, "valve")
    assert (PUMP, 0) not in fake.writes        # ch2 still needs the pump
    assert (CH1, 0) in fake.writes

    pc.deactivate(2, "valve")
    assert (PUMP, 0) in fake.writes            # last valve off -> pump drops


# 8 - re-running the same channel supersedes the in-flight timer
def test_same_channel_run_supersedes_previous_timer():
    pc, fake, timers = make_pc()
    pc.run_pump(1, 10, "pump")
    pc.run_pump(1, 10, "pump")
    assert timers[0].cancelled is True
    assert timers[1].cancelled is False
    assert pc.is_running(1)


# extra - concurrency limit defers a second channel (caller retries)
def test_max_concurrent_defers_second_channel():
    pc, fake, timers = make_pc(max_concurrent=1)
    assert pc.run_pump(1, 10, "pump") is not None
    assert pc.run_pump(2, 10, "pump") is None   # busy -> deferred
    assert not pc.is_running(2)


# extra - stop_all drives every channel and the pump LOW
def test_stop_all_drives_all_low():
    pc, fake, timers = make_pc(max_concurrent=5)
    pc.run_pump(1, 10, "valve")
    fake.writes.clear()
    assert pc.stop_all() is True
    low_pins = {pin for pin, value in fake.writes if value == 0}
    assert set(Pins.CHANNELS).issubset(low_pins)
    assert PUMP in low_pins
    assert not pc.is_running(1)
