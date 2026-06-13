# =============================================================================
# Pump controller — the single deep module that drives watering hardware safely.
#
# Replaces the old core/channel.setOutputState path for automatic watering. Every
# "pump on" is clamped to a hard maximum, always has a guaranteed "off" (via a
# timer plus try/finally), and reports real success/failure instead of always
# returning True. Hardware is reached only through a GpioAdapter so the module is
# unit-testable without lgpio / a Raspberry Pi.
#
# Scope note: this module owns GPIO for the *core* (automatic) path only. The
# Django API still drives pins via core/channel.py until phase 2; we therefore
# keep the per-operation claim/write/release lifecycle (in the adapter) so the
# two coexist without GPIO_BUSY conflicts.
# =============================================================================

import logging
import threading
from datetime import datetime

from gpioAdapter import GpioError

# Hard ceiling on how long any pump/valve may stay energised, regardless of the
# (unbounded) pumpDurationSeconds coming from the database. This is the flood
# guard.
MAX_PUMP_SECONDS = 300


class PumpError(Exception):
    '''Raised when a pump could not be started (e.g. the ON write failed).'''
    pass


# =============================================================================
class RunHandle:
    '''Returned by run_pump/activate. Wraps the auto-off timer so callers (and
    tests) can cancel it or wait for it to fire.'''

    def __init__(self, channel, timer):
        self.channel = channel
        self._timer = timer

    def cancel(self):
        self._timer.cancel()

    def wait(self, timeout=None):
        # threading.Timer is a Thread; FakeTimer in tests provides join() too.
        join = getattr(self._timer, "join", None)
        if join is not None:
            join(timeout)


# =============================================================================
class PumpController:

    def __init__(
        self,
        gpio,
        pins,
        channel_count=None,
        max_seconds=MAX_PUMP_SECONDS,
        max_concurrent=1,
        timer_factory=threading.Timer,
        clock=datetime.now,
        logger=None,
    ):
        self._gpio = gpio
        self._pins = pins
        self._channel_count = channel_count if channel_count is not None else len(pins.CHANNELS)
        self._max_seconds = max_seconds
        self._max_concurrent = max_concurrent
        self._timer_factory = timer_factory
        self._clock = clock
        self._log = logger or logging.getLogger("tethys.pump")

        self._lock = threading.RLock()
        self._timers = {}           # channel -> active auto-off timer
        self._active_valves = set() # valve channels currently energising the shared PUMP pin

    # -- public ---------------------------------------------------------------

    def run_pump(self, channel, seconds, channel_type, on_complete=None):
        '''Energise `channel` and guarantee it is switched off after the clamped
        duration. Non-blocking: returns a RunHandle immediately, or None if the
        controller is already at max_concurrent active pumps (the caller should
        leave its flag set and retry on the next loop pass).

        Raises ValueError for an out-of-range channel and PumpError if the ON
        write fails.'''
        self._validate(channel)
        seconds = self._clamp(seconds)

        with self._lock:
            # Busy guard: another channel is already pumping and we are at the
            # concurrency limit. Re-running the *same* channel is allowed (it
            # supersedes the in-flight run) and does not count against the limit.
            if channel not in self._timers and len(self._timers) >= self._max_concurrent:
                self._log.info(
                    "channel %s pump deferred: %s pump(s) already active",
                    channel, len(self._timers),
                )
                return None

            self._cancel_timer_locked(channel)

            start = self._clock()
            try:
                self._turn_on(channel, channel_type)
            except GpioError as e:
                # Never report success after a failed write. Best-effort off, then raise.
                self._safe_off(channel, channel_type)
                raise PumpError(f"failed to start pump on channel {channel}: {e}") from e

            timer = self._timer_factory(
                seconds, self._auto_off, args=(channel, channel_type, start, on_complete),
            )
            timer.daemon = True
            self._timers[channel] = timer
            timer.start()
            self._log.info("channel %s pumping for %ss (%s)", channel, seconds, channel_type)
            return RunHandle(channel, timer)

    def activate(self, channel, channel_type):
        '''Manual ON with a mandatory safety ceiling (auto-off after
        max_seconds), so a manual activate can never run forever.'''
        return self.run_pump(channel, self._max_seconds, channel_type)

    def deactivate(self, channel, channel_type):
        '''Explicit OFF. Cancels any pending auto-off timer and drives the line
        LOW. Returns the real result of the write (False on failure) — it never
        lies about success.'''
        self._validate(channel)
        with self._lock:
            self._cancel_timer_locked(channel)
            try:
                self._turn_off(channel, channel_type)
                return True
            except GpioError as e:
                self._log.error("channel %s deactivate failed: %s", channel, e)
                return False

    def is_running(self, channel):
        with self._lock:
            return channel in self._timers

    def stop_all(self):
        '''Cancel every timer and drive all channel pins and the PUMP pin LOW.
        Used for the fail-safe boot and the shutdown hook.'''
        with self._lock:
            for timer in list(self._timers.values()):
                timer.cancel()
            self._timers.clear()
            self._active_valves.clear()
            pins = list(self._pins.CHANNELS) + [self._pins.PUMP]
            try:
                self._gpio.write_pins(pins, 0)
            except GpioError as e:
                self._log.error("stop_all failed to drive pins LOW: %s", e)
                return False
            return True

    # shutdown is an alias used by the SIGTERM/atexit hook in tethys_core.
    shutdown = stop_all

    # -- internals ------------------------------------------------------------

    def _validate(self, channel):
        if not (1 <= channel <= self._channel_count):
            raise ValueError(
                f"channel {channel} out of range 1..{self._channel_count}"
            )

    def _clamp(self, seconds):
        if seconds is None:
            return 0
        return max(0, min(int(seconds), self._max_seconds))

    def _channel_pin(self, channel):
        return self._pins.CHANNELS[channel - 1]

    def _turn_on(self, channel, channel_type):
        if channel_type == 'valve':
            self._active_valves.add(channel)
            self._gpio.write_pins([self._channel_pin(channel), self._pins.PUMP], 1)
        else:
            self._gpio.write_pins([self._channel_pin(channel)], 1)

    def _turn_off(self, channel, channel_type):
        if channel_type == 'valve':
            self._active_valves.discard(channel)
            pins = [self._channel_pin(channel)]
            # Only drop the shared PUMP pin once no valve channel still needs it.
            if not self._active_valves:
                pins.append(self._pins.PUMP)
            self._gpio.write_pins(pins, 0)
        else:
            self._gpio.write_pins([self._channel_pin(channel)], 0)

    def _safe_off(self, channel, channel_type):
        try:
            self._turn_off(channel, channel_type)
        except GpioError as e:
            self._log.error("channel %s best-effort off failed: %s", channel, e)

    def _auto_off(self, channel, channel_type, start, on_complete):
        with self._lock:
            try:
                self._turn_off(channel, channel_type)   # guaranteed LOW attempt
            except GpioError as e:
                self._log.error("channel %s auto-off failed: %s", channel, e)
            finally:
                self._timers.pop(channel, None)
            end = self._clock()
        if on_complete is not None:
            try:
                on_complete(start, end)
            except Exception as e:  # a logging callback must never wedge the timer thread
                self._log.error("channel %s on_complete callback failed: %s", channel, e)

    def _cancel_timer_locked(self, channel):
        timer = self._timers.pop(channel, None)
        if timer is not None:
            timer.cancel()


# =============================================================================
def make_controller():
    '''Production wiring: the one place lgpio is bound to the controller. Drives
    all lines LOW on construction (fail-safe boot) since GPIO retains its last
    state across a bare process exit/restart.'''
    from gpioAdapter import LgpioAdapter
    from hardware import Pins

    controller = PumpController(LgpioAdapter(0), Pins)
    controller.stop_all()
    return controller
