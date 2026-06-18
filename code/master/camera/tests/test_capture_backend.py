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
