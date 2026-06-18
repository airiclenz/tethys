# =============================================================================
# Tests for the shared-API-key permission (tethys_api.permissions.ApiKeyRequired).
#
# Verifies the security contract after reads were locked down for safe remote
# (VPN) access: EVERY request needs a correct X-API-Key header, reads included;
# only the CORS preflight (OPTIONS) is exempt. The pump activate/deactivate
# endpoint is the worst-case target, so it is exercised end-to-end. The API no
# longer touches GPIO at all -- it enqueues a ManualCommand for the core to run --
# so a denied request is verified to enqueue nothing. The state-seeding
# initializeDatabase endpoint is verified to be a key-gated POST, not an open GET.
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

from unittest import mock

from django.conf import settings
from django.test import TestCase

from tethys_api.models import Channel, ChannelType, ManualCommand, TransmissionPowerLevel


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

    # -- reads are gated too --------------------------------------------------

    def test_get_denied_without_key(self):
        response = self.client.get("/api/channelSummary/")
        self.assertEqual(response.status_code, 403)

    def test_get_allowed_with_key(self):
        response = self.client.get("/api/channelSummary/", **_auth(self.key))
        self.assertEqual(response.status_code, 200)

    def test_options_preflight_is_open_without_key(self):
        # Only OPTIONS is exempt, so the browser's CORS preflight is never blocked.
        response = self.client.options("/api/channel/1/activate")
        self.assertNotEqual(response.status_code, 403)

    # -- pump activate is gated ----------------------------------------------

    def test_activate_denied_without_key(self):
        response = self.client.patch("/api/channel/1/activate")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ManualCommand.objects.exists())  # nothing enqueued when denied

    def test_activate_denied_with_wrong_key(self):
        response = self.client.patch("/api/channel/1/activate", **_auth("nope"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ManualCommand.objects.exists())

    def test_activate_allowed_with_key(self):
        response = self.client.patch("/api/channel/1/activate", **_auth(self.key))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(ManualCommand.objects.filter(channel=1, action="activate").count(), 1)

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

    # -- initializeDatabase is a key-gated POST, not an open GET --------------
    # (DRF checks permissions before method dispatch, so an unauthenticated GET
    # is denied at 403; a keyed GET reaches the method check and returns 405.)

    @mock.patch("tethys_api.views.ModelHelper.initializeDatabase")
    def test_initialize_db_get_denied_without_key(self, mock_init):
        response = self.client.get("/api/initializeDatabase/")
        self.assertEqual(response.status_code, 403)
        mock_init.assert_not_called()

    @mock.patch("tethys_api.views.ModelHelper.initializeDatabase")
    def test_initialize_db_get_method_not_allowed_with_key(self, mock_init):
        response = self.client.get("/api/initializeDatabase/", **_auth(self.key))
        self.assertEqual(response.status_code, 405)
        mock_init.assert_not_called()

    @mock.patch("tethys_api.views.ModelHelper.initializeDatabase")
    def test_initialize_db_post_denied_without_key(self, mock_init):
        response = self.client.post("/api/initializeDatabase/")
        self.assertEqual(response.status_code, 403)
        mock_init.assert_not_called()

    @mock.patch("tethys_api.views.ModelHelper.initializeDatabase")
    def test_initialize_db_post_allowed_with_key(self, mock_init):
        mock_init.return_value = {"ok": True}
        response = self.client.post("/api/initializeDatabase/", **_auth(self.key))
        self.assertEqual(response.status_code, 200)
        mock_init.assert_called_once()
