# =============================================================================
# Camera controller — the on-demand snapshot state machine.
#
# Holds the single "enabled" flag plus two privacy guards modelled on the pump
# controller's auto-off philosophy (core/pumpController.py): a fail-closed
# default, an idle auto-off, and a hard max-on ceiling. Hardware is reached only
# through a SnapshotBackend, so this is unit-testable with FakeSnapshotBackend
# and an injected timer_factory (the same seams the pump controller uses).
# =============================================================================

import logging
import threading
import time

import config


class CameraDisabledError(Exception):
    '''Raised when a snapshot is requested while capture is disabled. The HTTP
    layer maps this to 409 Conflict — "off" genuinely means no capture happens.'''
    pass


# =============================================================================
class CameraController:
    '''On-demand snapshot capture with three safety properties:

      - fail-closed: boots disabled; a snapshot while disabled raises
        CameraDisabledError, so capture never happens when "off".
      - idle auto-off: no snapshot fetched for idle_seconds -> auto-disable and
        release the device (browser closed/asleep).
      - hard max-on ceiling: auto-disable after max_on_seconds regardless of
        activity, so the camera can never be left on indefinitely.
    '''

    def __init__(
        self,
        backend,
        idle_seconds=config.IDLE_TIMEOUT_SECONDS,
        max_on_seconds=config.MAX_ON_SECONDS,
        timer_factory=threading.Timer,
        clock=time.monotonic,
        logger=None,
    ):
        self._backend = backend
        self._idle_seconds = idle_seconds
        self._max_on_seconds = max_on_seconds
        self._timer_factory = timer_factory
        self._clock = clock
        self._log = logger or logging.getLogger("tethys.camera")

        self._lock = threading.RLock()
        self._enabled = False
        self._idle_timer = None
        self._max_on_timer = None
        self._last_frame_at = None      # clock() reading of the most recent grab

    # -- public ---------------------------------------------------------------

    def start(self):
        '''Enable capture: open the device and arm both the idle auto-off and the
        hard max-on ceiling. Idempotent — a start while already enabled is a
        no-op and does not extend the max-on ceiling. Raises CaptureError if the
        backend fails to open.'''
        with self._lock:
            if self._enabled:
                return
            self._backend.start()       # may raise CaptureError; leaves us disabled
            self._enabled = True
            self._arm_idle_locked()
            self._arm_max_on_locked()
            self._log.info(
                "camera enabled (idle=%ss, max-on=%ss)",
                self._idle_seconds, self._max_on_seconds,
            )

    def stop(self):
        '''Disable capture, cancel both timers, and release the device.
        Idempotent.'''
        with self._lock:
            if not self._enabled:
                return
            self._disable_locked()
            self._log.info("camera disabled")

    def snapshot(self, width=None, height=None):
        '''Return one JPEG frame as bytes, optionally at the given capture size
        (None -> the backend's configured default). Raises CameraDisabledError if
        capture is disabled, or CaptureError if the grab fails. Each call resets
        the idle countdown (the request itself is the activity that keeps the
        device on). Resolution is per-request only — never stored, matching the
        one-shot grab model.'''
        with self._lock:
            if not self._enabled:
                raise CameraDisabledError("camera is disabled")

            self._arm_idle_locked()
            frame = self._backend.capture_jpeg(width, height)    # may raise CaptureError
            self._last_frame_at = self._clock()
            return frame

    def supported_resolutions(self):
        '''Capture resolutions the backend offers the UI dropdown. Empty when
        enumeration is unavailable; never raises (locked for symmetry with
        status()).'''
        with self._lock:
            return self._backend.supported_resolutions()

    def is_enabled(self):
        with self._lock:
            return self._enabled

    def status(self):
        '''Snapshot of state for the UI: whether capture is on, how long ago the
        last frame was served, the selected device, the refresh hint, and the
        selectable resolutions plus the default one.'''
        with self._lock:
            age = None
            if self._last_frame_at is not None:
                age = round(self._clock() - self._last_frame_at, 1)
            return {
                "enabled": self._enabled,
                "lastFrameAgeSec": age,
                "device": self._backend.device_name(),
                "refreshSeconds": config.SNAPSHOT_REFRESH_SECONDS,
                "resolutions": self._backend.supported_resolutions(),
                "defaultResolution": {
                    "width": config.CAPTURE_WIDTH,
                    "height": config.CAPTURE_HEIGHT,
                },
            }

    # -- internals ------------------------------------------------------------

    def _disable_locked(self):
        self._cancel_timers_locked()
        self._enabled = False
        try:
            self._backend.stop()
        except Exception as e:          # releasing must never wedge the caller
            self._log.error("camera backend stop failed: %s", e)

    def _auto_off(self, reason):
        '''Timer callback (runs on a timer thread): disable if still enabled.'''
        with self._lock:
            if not self._enabled:
                return
            self._log.info("camera auto-off (%s)", reason)
            self._disable_locked()

    def _arm_idle_locked(self):
        '''(Re)start the idle countdown. Cancels any pending one first, so each
        snapshot pushes the auto-off back out.'''
        if self._idle_timer is not None:
            self._idle_timer.cancel()
        self._idle_timer = self._new_timer(self._idle_seconds, "idle")

    def _arm_max_on_locked(self):
        '''Start the hard max-on ceiling. Armed once on enable and never reset by
        activity — that is what makes it a guaranteed ceiling.'''
        self._max_on_timer = self._new_timer(self._max_on_seconds, "max-on")

    def _new_timer(self, seconds, reason):
        timer = self._timer_factory(seconds, self._auto_off, args=(reason,))
        timer.daemon = True
        timer.start()
        return timer

    def _cancel_timers_locked(self):
        for timer in (self._idle_timer, self._max_on_timer):
            if timer is not None:
                timer.cancel()
        self._idle_timer = None
        self._max_on_timer = None
