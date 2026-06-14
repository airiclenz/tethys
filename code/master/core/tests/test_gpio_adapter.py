import sys
import types

import pytest

import gpioAdapter
from gpioAdapter import FakeGpioAdapter, GpioError, LgpioAdapter


def _fake_lgpio(calls, claim=None):
    class LgpioError(Exception):
        pass

    def claim_output(chip, pin):
        calls.append(("claim", chip, pin))
        if claim is not None:
            claim(pin)

    return types.SimpleNamespace(
        error=LgpioError,
        gpiochip_open=lambda n: calls.append(("open", n)) or "CHIP",
        gpio_claim_output=claim_output,
        gpio_write=lambda chip, pin, v: calls.append(("write", chip, pin, v)),
        gpiochip_close=lambda chip: calls.append(("close", chip)),
    )


def test_importing_module_does_not_bind_lgpio():
    # lgpio is imported lazily inside LgpioAdapter.__init__, never at module load.
    assert "lgpio" not in dir(gpioAdapter)


def test_lgpio_adapter_opens_claims_writes_closes(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "lgpio", _fake_lgpio(calls))
    adapter = LgpioAdapter(0)
    adapter.write_pins([16, 6], 1)
    assert ("open", 0) in calls
    assert ("claim", "CHIP", 16) in calls
    assert ("write", "CHIP", 16, 1) in calls
    assert ("write", "CHIP", 6, 1) in calls
    assert ("close", "CHIP") in calls           # always closes (finally)


def test_lgpio_adapter_translates_errors_and_still_closes(monkeypatch):
    calls = []

    def boom(pin):
        raise sys.modules["lgpio"].error("busy")

    monkeypatch.setitem(sys.modules, "lgpio", _fake_lgpio(calls, claim=boom))
    adapter = LgpioAdapter(0)
    with pytest.raises(GpioError):
        adapter.write_pins([16], 1)
    assert ("close", "CHIP") in calls           # closed despite the error


def test_fake_records_writes_in_order():
    fake = FakeGpioAdapter()
    fake.write_pins([16, 6], 1)
    fake.write_pins([16], 0)
    assert fake.writes == [(16, 1), (6, 1), (16, 0)]


def test_fake_fail_pins_raises_on_any_write():
    fake = FakeGpioAdapter()
    fake.fail_pins = {16}
    with pytest.raises(GpioError):
        fake.write_pins([16], 0)


def test_fake_fail_high_only_on_high():
    fake = FakeGpioAdapter()
    fake.fail_high = {16}
    with pytest.raises(GpioError):
        fake.write_pins([16], 1)
    fake.write_pins([16], 0)                     # LOW still works
    assert fake.writes == [(16, 0)]
