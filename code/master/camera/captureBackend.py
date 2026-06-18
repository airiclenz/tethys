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

    def capture_jpeg(self):
        '''Return a single JPEG frame as bytes. Raise CaptureError on failure.'''
        raise NotImplementedError

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
    ):
        self._device = device          # None -> resolve by capability on first use
        self._width = width
        self._height = height
        self._skip_frames = skip_frames
        self._timeout_seconds = timeout_seconds

    def capture_jpeg(self):
        device = self._resolve_device()

        fmt = f"width={self._width},height={self._height},pixelformat=MJPG"
        command = [
            "v4l2-ctl",
            "--device", device,
            "--set-fmt-video=" + fmt,
            "--stream-mmap",
            "--stream-skip=" + str(self._skip_frames),
            "--stream-count=1",
            "--stream-to=-",
        ]

        try:
            result = subprocess.run(
                command, capture_output=True, timeout=self._timeout_seconds,
            )
        except FileNotFoundError as e:
            raise CaptureError("v4l2-ctl not found; install v4l-utils") from e
        except subprocess.TimeoutExpired as e:
            raise CaptureError(
                f"camera grab timed out after {self._timeout_seconds}s"
            ) from e

        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise CaptureError(f"v4l2-ctl failed ({result.returncode}): {message}")

        frame = result.stdout
        if not frame.startswith(self._JPEG_SOI):
            raise CaptureError("grab returned no JPEG frame (wrong device node?)")

        return frame

    def device_name(self):
        return self._device

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


# =============================================================================
class Picamera2Backend(SnapshotBackend):
    '''Documented stub for a future Pi Camera Module (CSI) swap. It would run
    under the system Python with python3-picamera2 (open a Picamera2, capture to
    an in-memory JPEG, close on stop). Left unbuilt on purpose — the seam exists
    so adding it touches only this file.'''

    def capture_jpeg(self):
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

    def __init__(self, frame=None, fail=False):
        self.frame = frame if frame is not None else self.CANNED_JPEG
        self.fail = fail                # capture_jpeg raises CaptureError when True
        self.start_count = 0
        self.stop_count = 0
        self.capture_count = 0

    def start(self):
        self.start_count += 1

    def stop(self):
        self.stop_count += 1

    def capture_jpeg(self):
        self.capture_count += 1
        if self.fail:
            raise CaptureError("simulated capture failure")
        return self.frame

    def device_name(self):
        return "fake"
