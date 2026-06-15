# =============================================================================
# Latest-firmware lookup + comparison for the channel dashboard.
#
# The firmware version lives in exactly one place -- the sensor source header
# code/sensor/include/wpw_Version.h (VERSION.SUBVERSION.BUILDNUMBER) -- which
# both the firmware build and this dashboard read. "Latest" therefore means the
# newest version committed in *this* checkout, which on the Pi (where the master
# runs) is the right notion of "what a sensor should be running". A sensor that
# reports a newer version than the checkout shows as 'ahead' rather than an
# error: that just means the firmware tree here lags the bench.
#
# Everything here is best-effort and never raises: a missing or malformed
# header simply yields None / 'unknown' and the UI omits the up-to-date hint.
# =============================================================================

import re
from pathlib import Path

# This module is code/master/api/tethys_api/firmware.py; the firmware header is
# code/sensor/include/wpw_Version.h -- four parents up gets us to code/.
_VERSION_HEADER = (
    Path(__file__).resolve().parents[3] / "sensor" / "include" / "wpw_Version.h"
)

# Matches e.g. "#define   VERSION   3"; the \b stops VERSION matching inside
# PROTOCOL_VERSION etc. (wpw_Version.h has no such define, but be defensive).
_DEFINE_RE = re.compile(r"#define\s+(VERSION|SUBVERSION|BUILDNUMBER)\b\s+(\d+)")


# =============================================================================
def get_latest_firmware_version():
    """Return the latest firmware version as ``"major.minor.build"`` (e.g.
    ``"3.1.24"``) read from the sensor source header, or ``None`` if the header
    is missing or unparseable. Never raises."""
    try:
        text = _VERSION_HEADER.read_text()
    except OSError:
        return None

    parts = dict(_DEFINE_RE.findall(text))
    try:
        return f"{parts['VERSION']}.{parts['SUBVERSION']}.{parts['BUILDNUMBER']}"
    except KeyError:
        return None


# =============================================================================
def _as_tuple(version):
    """``"3.1.24"`` -> ``(3, 1, 24)``; ``None`` for anything that is not exactly
    three integer parts, so a malformed value compares as 'unknown' rather than
    crashing."""
    if not version:
        return None
    parts = version.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        return None


# =============================================================================
def firmware_status(reported, latest):
    """Classify a sensor's reported firmware against the latest known version.

    Returns one of ``"up_to_date"``, ``"outdated"``, ``"ahead"`` (sensor newer
    than this checkout) or ``"unknown"`` (either version missing / malformed)."""
    reportedTuple = _as_tuple(reported)
    latestTuple = _as_tuple(latest)

    if reportedTuple is None or latestTuple is None:
        return "unknown"
    if reportedTuple == latestTuple:
        return "up_to_date"
    return "outdated" if reportedTuple < latestTuple else "ahead"
