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


# A canned `v4l2-ctl --list-ctrls` block (focus 300-650, zoom 100-400, plus the
# continuous-AF control) — the verified C200's controls. The focus_absolute line
# carries `flags=inactive` (AF owns the lens) to prove the parser tolerates it.
LIST_CTRLS = (
    "                 focus_absolute 0x009a090a (int)    : min=300 max=650 step=1 default=300 value=300 flags=inactive\n"
    "     focus_automatic_continuous 0x009a090c (bool)   : default=1 value=1\n"
    "                  zoom_absolute 0x009a090d (int)    : min=100 max=400 step=1 default=100 value=295\n"
)


def fake_v4l2(captured, listing=LIST_CTRLS):
    '''A v4l2-ctl stub: answers `--list-ctrls` with `listing` (text, as the real
    tool does under text=True) and any other call with a minimal JPEG, appending
    each non-enumeration call to `captured["commands"]` in order. A focused grab
    now makes TWO such calls — a standalone AF-disable (`--set-ctrl=<af>=0`, no
    stream) committed first, then the grab itself (`--stream-mmap`) — so the
    recorder is a list, not a single slot.'''
    captured.setdefault("commands", [])
    def run(command, **kwargs):
        if "--list-ctrls" in command:
            return subprocess.CompletedProcess(command, 0, stdout=listing, stderr="")
        captured["commands"].append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"\xff\xd8\xff\xd9", stderr=b"")
    return run


def _grab(captured):
    '''The streaming grab among the recorded v4l2-ctl calls.'''
    return next(command for command in captured["commands"] if "--stream-mmap" in command)


def _af_disable(captured):
    '''The standalone AF-disable call (the only recorded call that doesn't stream),
    or None when no AF-disable step ran.'''
    pre = [command for command in captured["commands"] if "--stream-mmap" not in command]
    return pre[0] if pre else None


def test_capture_jpeg_applies_resolution_override(monkeypatch):
    '''An explicit (width, height) lands in the --set-fmt-video argument.'''
    backend = V4l2UsbBackend(focus=None, zoom=None)     # isolate the resolution arg
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(captured))

    backend.capture_jpeg(640, 480)

    assert "--set-fmt-video=width=640,height=480,pixelformat=MJPG" in _grab(captured)


# -- control enumeration ------------------------------------------------------
#
# supported_controls() shells `v4l2-ctl --list-ctrls`, parses the focus/zoom
# ranges, and must fail soft — status() depends on it never raising. The config
# seed (CAPTURE_FOCUS) positions the focus slider when it's within range; an
# unseeded control (zoom here) falls back to the camera's current value.

def test_supported_controls_parses_focus_and_zoom(monkeypatch):
    '''focus/zoom ranges are parsed; focus seeds to the configured 550, zoom to
    the camera's current 295; the continuous-AF control name is detected.'''
    backend = V4l2UsbBackend(focus=550, zoom=None)
    backend._device = "/dev/video0"
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2({}))

    controls = backend.supported_controls()

    assert controls["focus"] == {"min": 300, "max": 650, "step": 1, "value": 550}
    assert controls["zoom"] == {"min": 100, "max": 400, "step": 1, "value": 295}
    assert backend._af_control == "focus_automatic_continuous"


def test_supported_controls_fails_soft(monkeypatch):
    '''A wedged enumeration returns {} rather than raising, so status() can't throw.'''
    backend = V4l2UsbBackend()
    backend._device = "/dev/video0"

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="v4l2-ctl", timeout=5)

    monkeypatch.setattr("captureBackend.subprocess.run", _timeout)

    assert backend.supported_controls() == {}


# A camera with manual focus but NO continuous-AF control: focus is set directly
# (there's no INACTIVE flag to clear), so no AF-disable step should run — and the
# absent AF control must NOT be fabricated, which would wedge the grab.
LIST_CTRLS_NO_AF = (
    "                 focus_absolute 0x009a090a (int)    : min=300 max=650 step=1 default=300 value=300\n"
    "                  zoom_absolute 0x009a090d (int)    : min=100 max=400 step=1 default=100 value=295\n"
)


# -- per-request focus + zoom -------------------------------------------------
#
# Focus/zoom are applied per grab via --set-ctrl. Because focus_absolute and
# continuous AF form a UVC auto-cluster (focus_absolute is INACTIVE while AF owns
# the lens), AF is switched off in its OWN committed v4l2-ctl invocation FIRST;
# the grab then carries only the now-active controls. Packing AF-off and focus
# into one --set-ctrl leaves AF running — the bug these tests guard against.

def test_capture_jpeg_disables_af_then_applies_focus_and_zoom(monkeypatch):
    '''AF is switched off in a standalone invocation first; the grab then carries
    only focus_absolute/zoom_absolute (never AF packed in with focus), before the
    stream.'''
    backend = V4l2UsbBackend()
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(captured))

    backend.capture_jpeg(focus=600, zoom=200)

    af = _af_disable(captured)
    assert af == ["v4l2-ctl", "--device", "/dev/video0",
                  "--set-ctrl=focus_automatic_continuous=0"]

    grab = _grab(captured)
    ctrl = "--set-ctrl=focus_absolute=600,zoom_absolute=200"
    assert ctrl in grab
    assert grab.index(ctrl) < grab.index("--stream-mmap")
    assert not any("focus_automatic_continuous" in arg for arg in grab)

    # AF off was committed before the grab.
    assert captured["commands"].index(af) < captured["commands"].index(grab)


def test_capture_jpeg_uses_seed_default_focus(monkeypatch):
    '''With no per-request focus, the configured seed (550) is applied — AF off
    first, then focus_absolute on the grab.'''
    backend = V4l2UsbBackend(focus=550, zoom=None)
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(captured))

    backend.capture_jpeg()

    assert "--set-ctrl=focus_automatic_continuous=0" in _af_disable(captured)
    assert "--set-ctrl=focus_absolute=550" in _grab(captured)


def test_capture_jpeg_omits_unset_controls(monkeypatch):
    '''With nothing configured or requested, no AF-disable runs and the grab
    carries no --set-ctrl.'''
    backend = V4l2UsbBackend(focus=None, zoom=None)
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(captured))

    backend.capture_jpeg()

    assert _af_disable(captured) is None
    assert not any(arg.startswith("--set-ctrl") for arg in _grab(captured))


def test_capture_jpeg_skips_unsupported_control(monkeypatch):
    '''When enumeration shows no focus control, a focus value is dropped (it would
    wedge the grab) and no AF-disable runs, while a supported control (zoom) is
    still applied.'''
    zoom_only = "  zoom_absolute 0x009a090d (int)    : min=100 max=400 step=1 default=100 value=100\n"
    backend = V4l2UsbBackend(focus=550, zoom=None)
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(captured, listing=zoom_only))

    backend.capture_jpeg(focus=600, zoom=200)

    assert _af_disable(captured) is None
    grab = _grab(captured)
    assert not any("focus_absolute" in arg for arg in grab)
    assert any("zoom_absolute=200" in arg for arg in grab)


def test_capture_jpeg_no_af_control_sets_focus_directly(monkeypatch):
    '''A camera with manual focus but no continuous-AF control gets focus_absolute
    set directly — no AF-disable step, and no fabricated AF control name (which
    would make v4l2-ctl fail the whole grab).'''
    backend = V4l2UsbBackend(focus=550, zoom=None)
    backend._device = "/dev/video0"
    captured = {}
    monkeypatch.setattr(
        "captureBackend.subprocess.run", fake_v4l2(captured, listing=LIST_CTRLS_NO_AF)
    )

    backend.capture_jpeg(focus=600)

    assert _af_disable(captured) is None
    assert "--set-ctrl=focus_absolute=600" in _grab(captured)


def test_capture_jpeg_enumeration_unavailable_sets_focus_best_effort(monkeypatch):
    '''When control enumeration is unavailable (--list-ctrls times out), focus is
    still attempted best-effort, but no AF-disable runs — the AF control's name is
    unknown and naming a wrong one would wedge the grab.'''
    captured = {"commands": []}

    def run(command, **kwargs):
        if "--list-ctrls" in command:
            raise subprocess.TimeoutExpired(cmd="v4l2-ctl", timeout=5)
        captured["commands"].append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"\xff\xd8\xff\xd9", stderr=b"")

    backend = V4l2UsbBackend(focus=550, zoom=None)
    backend._device = "/dev/video0"
    monkeypatch.setattr("captureBackend.subprocess.run", run)

    backend.capture_jpeg(focus=600)

    assert _af_disable(captured) is None
    assert "--set-ctrl=focus_absolute=600" in _grab(captured)


def test_capture_jpeg_uses_settle_skip_on_focused_grab(monkeypatch):
    '''A grab that pins focus skips more frames (the focus motor needs time to
    travel to the new position); an unfocused grab keeps the small default.'''
    import config

    backend = V4l2UsbBackend(focus=None, zoom=None)
    backend._device = "/dev/video0"

    focused = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(focused))
    backend.capture_jpeg(focus=600)
    assert "--stream-skip=" + str(config.CAPTURE_FOCUS_SETTLE_SKIP_FRAMES) in _grab(focused)

    unfocused = {}
    monkeypatch.setattr("captureBackend.subprocess.run", fake_v4l2(unfocused))
    backend.capture_jpeg()
    assert "--stream-skip=" + str(config.CAPTURE_SKIP_FRAMES) in _grab(unfocused)
