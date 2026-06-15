# =============================================================================
# Tests for tethys_api.firmware: reading the latest firmware version from the
# sensor source header (wpw_Version.h) and classifying a sensor's reported
# version against it (up_to_date / outdated / ahead / unknown).
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

import re
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from tethys_api import firmware


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class FirmwareStatusTests(SimpleTestCase):

    def test_equal_versions_are_up_to_date(self):
        self.assertEqual(firmware.firmware_status("3.1.24", "3.1.24"), "up_to_date")

    def test_lower_build_is_outdated(self):
        self.assertEqual(firmware.firmware_status("3.1.20", "3.1.24"), "outdated")

    def test_lower_minor_is_outdated(self):
        self.assertEqual(firmware.firmware_status("3.0.99", "3.1.0"), "outdated")

    def test_lower_major_is_outdated(self):
        self.assertEqual(firmware.firmware_status("2.9.9", "3.0.0"), "outdated")

    def test_numeric_not_lexical_comparison(self):
        # "9" > "10" as strings; must compare as integers.
        self.assertEqual(firmware.firmware_status("3.1.9", "3.1.10"), "outdated")

    def test_higher_version_is_ahead(self):
        self.assertEqual(firmware.firmware_status("3.1.25", "3.1.24"), "ahead")

    def test_missing_reported_is_unknown(self):
        self.assertEqual(firmware.firmware_status("", "3.1.24"), "unknown")
        self.assertEqual(firmware.firmware_status(None, "3.1.24"), "unknown")

    def test_missing_latest_is_unknown(self):
        self.assertEqual(firmware.firmware_status("3.1.24", None), "unknown")

    def test_malformed_version_is_unknown(self):
        self.assertEqual(firmware.firmware_status("3.1", "3.1.24"), "unknown")
        self.assertEqual(firmware.firmware_status("3.1.x", "3.1.24"), "unknown")
        self.assertEqual(firmware.firmware_status("3.1.24.0", "3.1.24"), "unknown")


class GetLatestFirmwareVersionTests(SimpleTestCase):

    def _patch_header(self, contents):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".h", delete=False)
        tmp.write(contents)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return mock.patch.object(firmware, "_VERSION_HEADER", Path(tmp.name))

    def test_parses_define_block(self):
        header = (
            "#ifndef wpw_Version\n"
            "#define wpw_Version\n"
            "#define RELEASE\n"
            "#define   VERSION      5\n"
            "#define   SUBVERSION   2\n"
            "#define   BUILDNUMBER  7\n"
            "#endif\n"
        )
        with self._patch_header(header):
            self.assertEqual(firmware.get_latest_firmware_version(), "5.2.7")

    def test_release_define_without_number_is_ignored(self):
        # "#define RELEASE" has no value and must not break parsing.
        header = "#define RELEASE\n#define VERSION 1\n#define SUBVERSION 0\n#define BUILDNUMBER 3\n"
        with self._patch_header(header):
            self.assertEqual(firmware.get_latest_firmware_version(), "1.0.3")

    def test_incomplete_header_returns_none(self):
        header = "#define VERSION 3\n#define SUBVERSION 1\n"  # no BUILDNUMBER
        with self._patch_header(header):
            self.assertIsNone(firmware.get_latest_firmware_version())

    def test_missing_header_file_returns_none(self):
        with mock.patch.object(
                firmware, "_VERSION_HEADER", Path("/nonexistent/wpw_Version.h")):
            self.assertIsNone(firmware.get_latest_firmware_version())

    def test_real_header_resolves_and_parses(self):
        # The module's real path must resolve to the firmware header in this
        # checkout and yield a well-formed major.minor.build string.
        version = firmware.get_latest_firmware_version()
        self.assertIsNotNone(
            version, "wpw_Version.h not found at the path firmware.py computes")
        self.assertRegex(version, _SEMVER_RE)
