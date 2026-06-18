import subprocess

import pytest

from captureBackend import V4l2UsbBackend, CaptureError


# -- device resolution: distinguish "tool missing" from "node unqueryable" ----
#
# The probe (_resolve_device -> _device_caps) shells out to v4l2-ctl per node.
# A missing binary and a single wedged node must NOT be conflated: the former is
# fatal and actionable, the latter is skippable. These run without a camera by
# faking the node list and the v4l2-ctl subprocess.

def test_resolve_device_reports_missing_v4l2ctl(monkeypatch):
    '''v4l2-ctl unreachable (not on the unit's PATH, or v4l-utils not installed)
    must surface the actionable cause, not the misleading "no capture device
    found" that an empty probe would otherwise produce.'''
    def _missing(*args, **kwargs):
        raise FileNotFoundError("v4l2-ctl")

    monkeypatch.setattr("captureBackend.subprocess.run", _missing)
    monkeypatch.setattr("captureBackend.glob.glob", lambda _pattern: ["/dev/video0"])

    backend = V4l2UsbBackend()
    with pytest.raises(CaptureError, match="v4l2-ctl not found"):
        backend._resolve_device()


def test_resolve_device_skips_a_wedged_node(monkeypatch):
    '''A single node that times out is skipped, not fatal; with no usable node
    left, the probe ends with the generic "no capture device" error.'''
    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="v4l2-ctl", timeout=5)

    monkeypatch.setattr("captureBackend.subprocess.run", _timeout)
    monkeypatch.setattr("captureBackend.glob.glob", lambda _pattern: ["/dev/video0"])

    backend = V4l2UsbBackend()
    with pytest.raises(CaptureError, match="no V4L2 Video Capture device"):
        backend._resolve_device()


# -- resolution enumeration + per-request capture size ------------------------
#
# supported_resolutions() shells out to `v4l2-ctl --list-formats-ext` and must
# fail soft — status() depends on it never raising. capture_jpeg() takes an
# optional (width, height) override. Pre-seeding _device skips the capability
# probe so the only subprocess call under test is the one being asserted on.

LIST_FORMATS_EXT = (
    "\t[0]: 'MJPG' (Motion-JPEG, compressed)\n"
    "\t\tSize: Discrete 2560x1440\n"
    "\t\t\tInterval: Discrete 0.033s (30.000 fps)\n"
    "\t\tSize: Discrete 1920x1080\n"
    "\t\t\tInterval: Discrete 0.033s (30.000 fps)\n"
    "\t\tSize: Discrete 1280x720\n"
    "\t[1]: 'YUYV' (YUYV 4:2:2)\n"
    "\t\tSize: Discrete 640x480\n"
)


def test_supported_resolutions_parses_mjpg_block_only(monkeypatch):
    '''The MJPG sizes come back in device order; the YUYV size is excluded.'''
    backend = V4l2UsbBackend()
    backend._device = "/dev/video0"     # skip the capability probe

    def fake_run(command, **kwargs):
        assert "--list-formats-ext" in command
        return subprocess.CompletedProcess(command, 0, stdout=LIST_FORMATS_EXT, stderr="")

    monkeypatch.setattr("captureBackend.subprocess.run", fake_run)

    resolutions = backend.supported_resolutions()

    assert resolutions == [
        {"width": 2560, "height": 1440},
        {"width": 1920, "height": 1080},
        {"width": 1280, "height": 720},
    ]


def test_supported_resolutions_fails_soft(monkeypatch):
    '''A wedged enumeration returns [] rather than raising, so status() can't throw.'''
    backend = V4l2UsbBackend()
    backend._device = "/dev/video0"

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="v4l2-ctl", timeout=5)

    monkeypatch.setattr("captureBackend.subprocess.run", _timeout)

    assert backend.supported_resolutions() == []


def test_capture_jpeg_applies_resolution_override(monkeypatch):
    '''An explicit (width, height) lands in the --set-fmt-video argument.'''
    backend = V4l2UsbBackend()
    backend._device = "/dev/video0"
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=b"\xff\xd8\xff\xd9", stderr=b"")

    monkeypatch.setattr("captureBackend.subprocess.run", fake_run)

    backend.capture_jpeg(640, 480)

    assert "--set-fmt-video=width=640,height=480,pixelformat=MJPG" in captured["command"]
