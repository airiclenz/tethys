# =============================================================================
# Snapshot capture seam.
#
# The camera controller grabs JPEGs exclusively through a SnapshotBackend, so it
# never imports a camera library or shells out directly. Production wires in
# V4l2UsbBackend (a USB/UVC webcam via v4l2-ctl); tests wire in
# FakeSnapshotBackend. This is what makes the controller testable on a machine
# with no camera, and lets a Pi Camera Module (CSI) be swapped in later as one
# new class (Picamera2Backend) without touching the controller — exactly the
# shape core/gpioAdapter.py uses for the pump.
# =============================================================================

import glob
import re
import subprocess

import config


class CaptureError(Exception):
    '''Backend-neutral capture failure. Concrete backends translate their own
    errors (a subprocess failure, a missing device, a malformed frame) into this,
    so callers never depend on a specific camera library.'''
    pass


# =============================================================================
class SnapshotBackend:
    '''Minimal capture interface used by the camera controller.

    Lifecycle: start() when capture is enabled, capture_jpeg() per snapshot,
    stop() when disabled. The base start/stop are no-ops so a stateless backend
    (a one-shot grab) only needs to implement capture_jpeg().
    '''

    def start(self):
        '''Acquire / warm the device. Called when capture is enabled.'''
        pass

    def stop(self):
        '''Release the device. Called when capture is disabled.'''
        pass

    def capture_jpeg(self, width=None, height=None, focus=None, zoom=None):
        '''Return a single JPEG frame as bytes, optionally at the given capture
        size and focus/zoom (None -> the backend's configured default for each).
        Raise CaptureError on failure.'''
        raise NotImplementedError

    def supported_resolutions(self):
        '''Capture resolutions this backend can offer the UI dropdown, as
        [{"width": W, "height": H}, ...]. Empty when enumeration is unavailable
        (the default), which degrades the client to "no dropdown". Must never
        raise — status() depends on this.'''
        return []

    def supported_controls(self):
        '''Adjustable controls this backend can offer the UI as sliders, as
        {"focus": {"min": .., "max": .., "step": .., "value": ..}, "zoom": {..}}.
        Only includes controls the camera actually exposes, so the UI disables
        the rest. Empty when enumeration is unavailable (the default). Must never
        raise — status() depends on this.'''
        return {}

    def device_name(self):
        '''Human-readable device identifier for the status endpoint, or None if
        not yet known.'''
        return None


# =============================================================================
class V4l2UsbBackend(SnapshotBackend):
    '''Production backend for a USB/UVC webcam via v4l2-ctl (already present on
    the Pi — no extra Python dependency, and no transcoding for an MJPG-native
    camera like the verified Anker C200).

    A grab is a one-shot subprocess, so the device is opened and released per
    snapshot; CAPTURE_SKIP_FRAMES drops the first few frames each time so
    auto-exposure has settled before the kept frame.
    '''

    # SOI marker every JPEG (and MJPG frame) begins with. A wrong device node
    # (e.g. the metadata sibling) streams forever and yields zero image bytes, so
    # this prefix check also catches a mis-selected node.
    _JPEG_SOI = b"\xff\xd8"

    def __init__(
        self,
        device=None,
        width=config.CAPTURE_WIDTH,
        height=config.CAPTURE_HEIGHT,
        skip_frames=config.CAPTURE_SKIP_FRAMES,
        timeout_seconds=config.CAPTURE_TIMEOUT_SECONDS,
        focus=config.CAPTURE_FOCUS,
        zoom=config.CAPTURE_ZOOM,
    ):
        self._device = device          # None -> resolve by capability on first use
        self._width = width
        self._height = height
        self._skip_frames = skip_frames
        self._timeout_seconds = timeout_seconds
        self._focus = focus            # seed default; None -> leave focus untouched
        self._zoom = zoom              # seed default; None -> leave zoom untouched
        self._resolutions = None        # None -> enumerate on first use; [] never cached
        self._controls = None          # None -> not probed; dict (maybe empty) once probed OK
        self._af_control = None        # continuous-AF control name, if the camera has one

    def capture_jpeg(self, width=None, height=None, focus=None, zoom=None):
        device = self._resolve_device()
        af_disable, ctrls, focus_pinned = self._resolve_controls(focus, zoom)

        # Disable continuous AF in its own committed invocation BEFORE the grab.
        # focus_absolute and continuous AF form a UVC auto-cluster: focus_absolute
        # is flagged INACTIVE while AF owns the lens, so setting AF=off and
        # focus_absolute in the *same* VIDIOC_S_EXT_CTRLS is validated against the
        # pre-call state and the focus write is dropped — AF never actually turns
        # off and the lens keeps hunting. A separate v4l2-ctl run commits AF off
        # (UVC keeps that across the sub-second reopen, and --set-fmt-video below
        # doesn't reset it), so the grab's focus_absolute then takes. Best-effort:
        # a camera that won't take the AF-off still yields a frame (the grab that
        # follows surfaces any real failure, e.g. a missing v4l2-ctl).
        if af_disable:
            self._run_v4l2(
                ["v4l2-ctl", "--device", device, "--set-ctrl=" + af_disable + "=0"],
                check=False,
            )

        capture_width = width if width is not None else self._width
        capture_height = height if height is not None else self._height
        fmt = f"width={capture_width},height={capture_height},pixelformat=MJPG"
        command = ["v4l2-ctl", "--device", device, "--set-fmt-video=" + fmt]

        if ctrls:
            # The now-active controls (focus_absolute / zoom_absolute). Sits before
            # --stream-mmap so v4l2-ctl applies them ahead of streaming, in the
            # same invocation as the grab.
            command.append("--set-ctrl=" + ctrls)

        # A grab that pins focus skips more frames: the focus motor needs a few
        # hundred ms to travel to the new position, so the default couple of skip
        # frames would catch the lens mid-travel and look like AF still hunting.
        skip = self._skip_frames
        if focus_pinned:
            skip = max(skip, config.CAPTURE_FOCUS_SETTLE_SKIP_FRAMES)
        command += [
            "--stream-mmap",
            "--stream-skip=" + str(skip),
            "--stream-count=1",
            "--stream-to=-",
        ]

        try:
            result = self._run_v4l2(command, check=True)

            frame = result.stdout
            if not frame.startswith(self._JPEG_SOI):
                raise CaptureError("grab returned no JPEG frame (wrong device node?)")
        except CaptureError:
            # A failed grab is most often the device dropping off the bus (the C200
            # EPROTO-disconnects mid-session). That leaves the cached node stale, so
            # every later grab fails against a /dev/video* that no longer exists.
            # Forget it so the next snapshot re-probes and picks up the node a USB
            # recovery re-enumerates the camera as — self-correcting even if this
            # process isn't restarted. (A full recovery also restarts the service,
            # which clears every cache; this is the in-process safety net.)
            self._device = None
            raise

        return frame

    def _run_v4l2(self, command, check):
        '''Run a v4l2-ctl command. With check=True (the grab) a missing tool,
        timeout, or non-zero exit becomes a CaptureError. With check=False (the
        best-effort AF-disable pre-step) every failure is swallowed and None is
        returned — a camera that won't take the AF-off still gets a frame, and any
        genuine problem surfaces on the grab that follows.'''
        try:
            result = subprocess.run(
                command, capture_output=True, timeout=self._timeout_seconds,
            )
        except FileNotFoundError as e:
            if not check:
                return None
            raise CaptureError("v4l2-ctl not found; install v4l-utils") from e
        except subprocess.TimeoutExpired as e:
            if not check:
                return None
            raise CaptureError(
                f"camera grab timed out after {self._timeout_seconds}s"
            ) from e

        if check and result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise CaptureError(f"v4l2-ctl failed ({result.returncode}): {message}")
        return result

    def device_name(self):
        return self._device

    def supported_resolutions(self):
        '''Resolutions the camera advertises for MJPG capture, in device order
        (typically largest-first), for the UI dropdown. Mirrors _resolve_device's
        cache-on-success and _device_caps' subprocess/parse idioms, but fails
        soft: any failure (no capture node, missing tool, wedged or empty probe)
        returns [] rather than raising, because status() must never throw. Only a
        non-empty result is cached, so a camera plugged in after a failed probe is
        still picked up on a later call.'''
        if self._resolutions:
            return self._resolutions

        try:
            device = self._resolve_device()
        except CaptureError:
            return []                   # no capture node yet — retry next call

        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", device, "--list-formats-ext"],
                capture_output=True, timeout=self._timeout_seconds, text=True,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0:
            return []

        resolutions = self._parse_resolutions(result.stdout)
        if resolutions:
            self._resolutions = resolutions
        return resolutions

    def supported_controls(self):
        '''The focus/zoom controls the camera advertises, for the UI sliders, as
        {"focus": {"min": .., "max": .., "step": .., "value": ..}, "zoom": {..}}
        with only the controls the camera actually exposes. Shells
        `v4l2-ctl --list-ctrls` and, like supported_resolutions(), fails soft —
        any failure returns {} rather than raising, because status() must never
        throw. Unlike resolutions, a successful-but-empty probe IS cached: "this
        camera has no focus/zoom" is a stable answer worth not re-probing. Only a
        failed probe is left uncached so a later call retries.'''
        if self._controls is not None:
            return self._controls

        try:
            device = self._resolve_device()
        except CaptureError:
            return {}                   # no capture node yet — retry next call

        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", device, "--list-ctrls"],
                capture_output=True, timeout=self._timeout_seconds, text=True,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        if result.returncode != 0:
            return {}

        ranges, self._af_control = self._parse_controls(result.stdout)
        self._controls = self._seed_initial_values(ranges)
        return self._controls

    def _resolve_controls(self, focus, zoom):
        '''Work out the camera controls for this grab. Returns
        (af_disable, active, focus_pinned):
          - af_disable: the continuous-AF control name to switch off in its own
            committed invocation before the grab (so focus_absolute is no longer
            INACTIVE when set), or None when no AF needs disabling;
          - active: the comma-joined `--set-ctrl` value for the grab itself — the
            controls that are active once AF is off (focus_absolute / zoom_absolute)
            — or "" when nothing applies;
          - focus_pinned: True when focus_absolute is being set (the caller then
            uses the larger settle skip so the moved lens isn't caught mid-travel).
        A per-request focus/zoom wins; otherwise the seed default
        (config.CAPTURE_FOCUS / CAPTURE_ZOOM) is used. A control is emitted only
        when the camera exposes it (or enumeration was unavailable, in which case
        focus/zoom are attempted best-effort) — so a value can never wedge the grab
        on a camera that lacks the control.'''
        controls = self.supported_controls()       # cached; populates _af_control
        focus = focus if focus is not None else self._focus
        zoom = zoom if zoom is not None else self._zoom

        af_disable = None
        active = []
        focus_pinned = False
        if focus is not None and (not controls or "focus" in controls):
            # Only switch off an AF control the camera actually advertises: naming
            # one it lacks would make v4l2-ctl fail the whole grab. A camera with
            # manual focus and no continuous-AF control (or one we couldn't
            # enumerate) has no INACTIVE flag to clear, so we set focus_absolute
            # directly and skip the AF-disable step.
            if self._af_control:
                af_disable = self._af_control
            active.append(f"focus_absolute={focus}")
            focus_pinned = True
        if zoom is not None and (not controls or "zoom" in controls):
            active.append(f"zoom_absolute={zoom}")
        return af_disable, ",".join(active), focus_pinned

    # -- device selection -----------------------------------------------------

    def _resolve_device(self):
        '''Pick the capture node by capability, not index. A single USB camera
        exposes a capture node AND a metadata-only node (e.g. /dev/video0 +
        /dev/video1), and the Pi adds its own codec/ISP nodes (/dev/video10+);
        opening the wrong one yields zero image bytes. Probe for a pure Video
        Capture node and cache it once found.'''
        if self._device is not None:
            return self._device

        for node in sorted(glob.glob("/dev/video*")):
            if self._is_video_capture_node(node):
                self._device = node
                return node

        raise CaptureError("no V4L2 Video Capture device found under /dev/video*")

    def _is_video_capture_node(self, node):
        '''True only for a pure capture node: its Device Caps list "Video Capture"
        but not "Memory-to-Memory" (the Pi codec nodes) nor "Video Output" (the
        ISP nodes); the metadata sibling lists only "Metadata Capture". The
        Device Caps block (per-node) must be read specifically — the Driver Caps
        block reports the union across the physical device's nodes and would
        falsely match the metadata sibling.'''
        caps = self._device_caps(node)
        if not caps:
            return False
        names = " ".join(caps)
        if "Memory-to-Memory" in names or "Video Output" in names:
            return False
        return "Video Capture" in names

    def _device_caps(self, node):
        '''Return the capability lines under the node's "Device Caps" header, or
        an empty list if this particular node can't be queried.'''
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", node, "--all"],
                capture_output=True, timeout=self._timeout_seconds, text=True,
            )
        except FileNotFoundError as e:
            # v4l2-ctl itself is missing/unreachable (not on PATH, not installed):
            # every node would fail identically, so the probe would come up empty
            # and _resolve_device would raise the misleading "no capture device
            # found". Surface the actionable cause instead — same message and
            # CaptureError type the grab path (capture_jpeg) already raises.
            raise CaptureError("v4l2-ctl not found; install v4l-utils") from e
        except subprocess.TimeoutExpired:
            return []           # this one node is wedged; skip it, keep probing
        if result.returncode != 0:
            return []

        caps = []
        in_block = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not in_block:
                if stripped.startswith("Device Caps"):
                    in_block = True
                continue
            # Capability lines are indented; a new top-level section starts at
            # column 0 and ends the block.
            if line[:1] in (" ", "\t") and stripped:
                caps.append(stripped)
            elif stripped:
                break
        return caps

    def _parse_resolutions(self, listing):
        '''Pull the discrete MJPG sizes out of `v4l2-ctl --list-formats-ext`. The
        listing groups sizes under a per-format header (e.g. "[0]: 'MJPG'"); we
        collect "Size: Discrete WxH" lines only while inside the MJPG block, so
        YUYV/H264 sizes are excluded. Device order is preserved.'''
        resolutions = []
        in_mjpg = False
        for line in listing.splitlines():
            header = re.match(r"\s*\[\d+\]:\s*'(\w+)'", line)
            if header:
                in_mjpg = header.group(1) == "MJPG"
                continue
            if in_mjpg:
                size = re.search(r"Size:\s*Discrete\s*(\d+)x(\d+)", line)
                if size:
                    resolutions.append(
                        {"width": int(size.group(1)), "height": int(size.group(2))}
                    )
        return resolutions

    # v4l2 control names -> the keys the UI/router speak. Only these two are
    # surfaced as sliders; adding more later is one entry each.
    _UI_CONTROLS = {"focus_absolute": "focus", "zoom_absolute": "zoom"}
    # Continuous-AF control names across kernels: modern first, pre-5.x fallback.
    _AF_CONTROLS = ("focus_automatic_continuous", "focus_auto")

    def _parse_controls(self, listing):
        '''Parse `v4l2-ctl --list-ctrls` into (ranges, af_control). `ranges` maps
        each UI control the camera lists to its raw {min, max, step, default,
        value}; `af_control` is the name of the camera's continuous-AF control if
        present (so capture_jpeg knows which one to switch off before pinning
        focus), else None. A control the camera omits is simply absent from
        `ranges`, which is what lets the UI disable its slider. The `flags=...`
        suffix some controls carry (e.g. focus_absolute "inactive" while AF owns
        the lens) is ignored — it's not an int field and the control is still
        listed.'''
        ranges = {}
        af_control = None
        for line in listing.splitlines():
            match = re.match(
                r"\s*(\w+)\s+0x[0-9a-fA-F]+\s+\((\w+)\)\s*:\s*(.*)", line
            )
            if not match:
                continue
            name, ctype, rest = match.group(1), match.group(2), match.group(3)
            if name in self._AF_CONTROLS:
                af_control = name
                continue
            ui_name = self._UI_CONTROLS.get(name)
            if ui_name and ctype == "int":
                fields = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", rest)}
                if "min" in fields and "max" in fields:
                    ranges[ui_name] = fields
        return ranges, af_control

    def _seed_initial_values(self, ranges):
        '''Turn raw control ranges into the UI payload {control: {min, max, step,
        value}}. `value` is the slider's starting position: the configured seed
        (config.CAPTURE_FOCUS / CAPTURE_ZOOM) when set and within the camera's
        range, else the camera's own current value (falling back to its default,
        then min). The browser's localStorage can still override this per
        device — this is just the fresh-browser / no-override default.'''
        seeds = {"focus": self._focus, "zoom": self._zoom}
        controls = {}
        for name, fields in ranges.items():
            low, high = fields["min"], fields["max"]
            seed = seeds.get(name)
            if seed is not None and low <= seed <= high:
                value = seed
            else:
                value = fields.get("value", fields.get("default", low))
            controls[name] = {
                "min": low,
                "max": high,
                "step": fields.get("step", 1),
                "value": value,
            }
        return controls


# =============================================================================
class Picamera2Backend(SnapshotBackend):
    '''Documented stub for a future Pi Camera Module (CSI) swap. It would run
    under the system Python with python3-picamera2 (open a Picamera2, capture to
    an in-memory JPEG, close on stop). Left unbuilt on purpose — the seam exists
    so adding it touches only this file.'''

    def capture_jpeg(self, width=None, height=None, focus=None, zoom=None):
        raise CaptureError(
            "Picamera2Backend is not implemented; use V4l2UsbBackend for USB cameras"
        )


# =============================================================================
class FakeSnapshotBackend(SnapshotBackend):
    '''In-memory backend for tests. Returns a canned minimal JPEG and records the
    start/stop lifecycle so tests can assert the device is opened on enable and
    released on disable — mirroring core/gpioAdapter.py's FakeGpioAdapter.'''

    # Smallest valid-enough stand-in: the SOI..EOI markers the controller and the
    # HTTP layer treat as "a JPEG". Tests never decode it.
    CANNED_JPEG = b"\xff\xd8\xff\xd9"

    # A canned device-derived list so the controller/router can be exercised
    # against resolution validation without a camera.
    CANNED_RESOLUTIONS = [
        {"width": 1280, "height": 720},
        {"width": 640, "height": 480},
    ]

    # Canned focus/zoom ranges so the controller/router can be exercised against
    # control validation without a camera (focus 300-650, zoom 100-400 — the
    # verified C200's ranges).
    CANNED_CONTROLS = {
        "focus": {"min": 300, "max": 650, "step": 1, "value": 550},
        "zoom": {"min": 100, "max": 400, "step": 1, "value": 100},
    }

    def __init__(self, frame=None, fail=False):
        self.frame = frame if frame is not None else self.CANNED_JPEG
        self.fail = fail                # capture_jpeg raises CaptureError when True
        self.start_count = 0
        self.stop_count = 0
        self.capture_count = 0
        self.last_capture = None        # (width, height, focus, zoom) of the last grab

    def start(self):
        self.start_count += 1

    def stop(self):
        self.stop_count += 1

    def capture_jpeg(self, width=None, height=None, focus=None, zoom=None):
        self.capture_count += 1
        self.last_capture = (width, height, focus, zoom)
        if self.fail:
            raise CaptureError("simulated capture failure")
        return self.frame

    def supported_resolutions(self):
        return list(self.CANNED_RESOLUTIONS)

    def supported_controls(self):
        return {name: dict(spec) for name, spec in self.CANNED_CONTROLS.items()}

    def device_name(self):
        return "fake"
