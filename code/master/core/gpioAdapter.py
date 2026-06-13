# =============================================================================
# GPIO adapter seam.
#
# The pump controller drives the hardware exclusively through a GpioAdapter, so
# the controller itself never imports lgpio. Production wires in LgpioAdapter;
# tests wire in FakeGpioAdapter. This is what makes the controller testable on a
# dev machine that has no lgpio / no Raspberry Pi hardware.
# =============================================================================


class GpioError(Exception):
    '''Adapter-neutral GPIO failure. Concrete adapters translate their backend's
    errors (e.g. lgpio.error) into this, so callers never depend on lgpio.'''
    pass


# =============================================================================
class GpioAdapter:
    '''Minimal output-pin interface used by the pump controller.

    Implementations claim a pin as an output, write a level (0/1) and release.
    The lifecycle is intentionally per-operation (open -> claim -> write ->
    close) so this adapter coexists with the Django API's existing per-call GPIO
    access; a persistent claim on the same lines would make the other process's
    gpio_claim_output fail with GPIO_BUSY.
    '''

    def write_pins(self, pins, value):
        '''Drive every pin in `pins` (an iterable of BCM pin numbers) to `value`
        (0 or 1) as a single claimed operation. Raise GpioError on failure.'''
        raise NotImplementedError


# =============================================================================
class LgpioAdapter(GpioAdapter):
    '''Production adapter backed by lgpio.

    lgpio is imported lazily inside __init__ so that importing this module (and
    running the test suite) does not require lgpio to be installed.
    '''

    def __init__(self, chip_number=0):
        import lgpio  # lazy: only the production path needs the C extension
        self._lgpio = lgpio
        self._chip_number = chip_number

    def write_pins(self, pins, value):
        chip = None
        try:
            chip = self._lgpio.gpiochip_open(self._chip_number)
            for pin in pins:
                self._lgpio.gpio_claim_output(chip, pin)
                self._lgpio.gpio_write(chip, pin, int(value))
        except self._lgpio.error as e:
            raise GpioError(str(e)) from e
        finally:
            if chip is not None:
                try:
                    self._lgpio.gpiochip_close(chip)
                except self._lgpio.error:
                    pass  # closing failed; nothing useful to do, don't mask the real error


# =============================================================================
class FakeGpioAdapter(GpioAdapter):
    '''In-memory adapter for tests. Records every write in order so tests can
    assert exact pin/level sequences, and can be told to fail specific pins to
    simulate GPIO_BUSY / a stuck line.'''

    def __init__(self):
        self.writes = []            # list of (pin, value) in call order
        self.fail_pins = set()      # pins whose write always raises GpioError
        self.fail_high = set()      # pins that fail only when driven HIGH (1)

    def write_pins(self, pins, value):
        value = int(value)
        for pin in pins:
            if pin in self.fail_pins or (value == 1 and pin in self.fail_high):
                raise GpioError(f"simulated GPIO failure on pin {pin} (value={value})")
            self.writes.append((pin, value))
