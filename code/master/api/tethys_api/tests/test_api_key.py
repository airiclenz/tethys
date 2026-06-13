# =============================================================================
# Tests for the shared-API-key permission (tethys_api.permissions.ApiKeyForWrite).
#
# Verifies the security contract: read-only requests stay open, but every
# mutating request requires a correct X-API-Key header. The pump
# activate/deactivate endpoint is the worst-case target, so it is exercised
# end-to-end (with the hardware call mocked out so no GPIO is touched).
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

from unittest import mock

from django.conf import settings
from django.test import TestCase

from tethys_api.models import Channel, ChannelType, TransmissionPowerLevel


def _auth(key):
    '''Header kwargs for the Django/DRF test client.'''
    return {"HTTP_X_API_KEY": key}


class ApiKeyPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.key = settings.TETHYS_API_KEY
        valve = ChannelType.objects.create(name="valve")
        power = TransmissionPowerLevel.objects.create(name="min", value=0)
        Channel.objects.create(
            number=1,
            enabled=True,
            nickName="Test",
            channelType=valve,
            actionTriggerPercent=50,
            pumpDurationSeconds=10,
            sensorMeasureFrequencyMinutes=60,
            sensorTransmissionPowerLevel=power,
        )

    # -- reads stay open ------------------------------------------------------

    def test_get_is_open_without_key(self):
        response = self.client.get("/api/channelSummary/")
        self.assertEqual(response.status_code, 200)

    def test_options_preflight_is_open_without_key(self):
        # SAFE_METHODS includes OPTIONS, so the CORS preflight is never blocked.
        response = self.client.options("/api/channel/1/activate")
        self.assertNotEqual(response.status_code, 403)

    # -- pump activate is gated ----------------------------------------------

    @mock.patch("tethys_api.views.hardwareChannel.setOutputState")
    def test_activate_denied_without_key(self, mock_set):
        response = self.client.patch("/api/channel/1/activate")
        self.assertEqual(response.status_code, 403)
        mock_set.assert_not_called()  # hardware must not be touched when denied

    @mock.patch("tethys_api.views.hardwareChannel.setOutputState")
    def test_activate_denied_with_wrong_key(self, mock_set):
        response = self.client.patch("/api/channel/1/activate", **_auth("nope"))
        self.assertEqual(response.status_code, 403)
        mock_set.assert_not_called()

    @mock.patch("tethys_api.views.hardwareChannel.setOutputState")
    def test_activate_allowed_with_key(self, mock_set):
        response = self.client.patch("/api/channel/1/activate", **_auth(self.key))
        self.assertEqual(response.status_code, 202)
        mock_set.assert_called_once()

    # -- a representative POST is gated --------------------------------------

    def test_post_denied_without_key(self):
        response = self.client.post(
            "/api/channelType/", data={"name": "drip"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ChannelType.objects.filter(name="drip").exists())

    def test_post_allowed_with_key(self):
        response = self.client.post(
            "/api/channelType/",
            data={"name": "drip"},
            content_type="application/json",
            **_auth(self.key),
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ChannelType.objects.filter(name="drip").exists())
