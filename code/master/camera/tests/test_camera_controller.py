import pytest

from captureBackend import FakeSnapshotBackend, CaptureError
from cameraController import CameraController, CameraDisabledError

from tests._helpers import collecting_timer_factory


def make_controller(backend=None, idle_seconds=15, max_on_seconds=1800):
    '''Controller wired to a fake backend and non-running timers. Returns
    (controller, backend, list_of_created_timers).'''
    backend = backend if backend is not None else FakeSnapshotBackend()
    factory, timers = collecting_timer_factory()

    controller = CameraController(
        backend,
        idle_seconds=idle_seconds,
        max_on_seconds=max_on_seconds,
        timer_factory=factory,
    )
    return controller, backend, timers


def idle_timers(timers):
    return [timer for timer in timers if timer.args == ("idle",)]


def max_on_timers(timers):
    return [timer for timer in timers if timer.args == ("max-on",)]


# 1 - fail-closed: a snapshot before start is refused (HTTP layer maps to 409)
def test_snapshot_while_disabled_raises():
    controller, backend, _ = make_controller()

    with pytest.raises(CameraDisabledError):
        controller.snapshot()

    assert backend.capture_count == 0


# 2 - start opens the device; a snapshot then returns a JPEG (HTTP 200)
def test_start_then_snapshot_returns_frame():
    controller, backend, _ = make_controller()

    controller.start()
    frame = controller.snapshot()

    assert controller.is_enabled()
    assert backend.start_count == 1
    assert frame == FakeSnapshotBackend.CANNED_JPEG
    assert backend.capture_count == 1


# 3 - start arms both guards and is idempotent (no re-open, no extra ceiling)
def test_start_is_idempotent():
    controller, backend, timers = make_controller()

    controller.start()
    controller.start()

    assert backend.start_count == 1
    assert len(idle_timers(timers)) == 1
    assert len(max_on_timers(timers)) == 1


# 4 - each snapshot pushes the idle auto-off back out (cancels old, arms new)
def test_snapshot_resets_idle_timer():
    controller, _, timers = make_controller()
    controller.start()
    first_idle = idle_timers(timers)[0]

    controller.snapshot()

    idles = idle_timers(timers)
    assert len(idles) == 2
    assert first_idle.cancelled
    assert idles[1].started


# 5 - the idle timer firing auto-disables and releases the device
def test_idle_timer_auto_disables():
    controller, backend, timers = make_controller()
    controller.start()

    idle_timers(timers)[0].fire()

    assert not controller.is_enabled()
    assert backend.stop_count == 1
    with pytest.raises(CameraDisabledError):
        controller.snapshot()


# 6 - the hard max-on ceiling firing auto-disables even with recent activity
def test_max_on_ceiling_auto_disables():
    controller, backend, timers = make_controller()
    controller.start()
    controller.snapshot()                   # activity resets idle, never max-on

    max_on_timers(timers)[0].fire()

    assert not controller.is_enabled()
    assert backend.stop_count == 1


# 7 - explicit stop releases the device and cancels both timers
def test_stop_releases_and_cancels_timers():
    controller, backend, timers = make_controller()
    controller.start()

    controller.stop()

    assert not controller.is_enabled()
    assert backend.stop_count == 1
    assert idle_timers(timers)[0].cancelled
    assert max_on_timers(timers)[0].cancelled


# 8 - a failed grab surfaces CaptureError but leaves the camera enabled to retry
def test_capture_failure_keeps_camera_enabled():
    controller, _, _ = make_controller(backend=FakeSnapshotBackend(fail=True))
    controller.start()

    with pytest.raises(CaptureError):
        controller.snapshot()

    assert controller.is_enabled()
