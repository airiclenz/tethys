# =============================================================================
# Tests for the manual-command queue that replaced the API's direct-GPIO path.
#
# The web "Test Channel" toggle no longer drives GPIO from the API process; it
# enqueues a ManualCommand that the core (the single owner of the watering
# hardware) drains and runs through the pump controller. These tests cover the
# API half: enqueue, the pending list the core polls, and the result write-back
# the UI polls.
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

from django.conf import settings
from django.test import TestCase

from tethys_api.models import Channel, ChannelType, ManualCommand, TransmissionPowerLevel


def _auth(key):
    '''Header kwargs for the Django/DRF test client.'''
    return {"HTTP_X_API_KEY": key}


class ManualCommandQueueTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.key = settings.TETHYS_API_KEY
        valve = ChannelType.objects.create(name="valve")
        power = TransmissionPowerLevel.objects.create(name="min", value=0)
        cls.enabledChannel = Channel.objects.create(
            number=1, enabled=True, nickName="Enabled", channelType=valve,
            actionTriggerPercent=50, pumpDurationSeconds=10,
            sensorMeasureFrequencyMinutes=60, sensorTransmissionPowerLevel=power,
        )
        Channel.objects.create(
            number=2, enabled=False, nickName="Disabled", channelType=valve,
            actionTriggerPercent=50, pumpDurationSeconds=10,
            sensorMeasureFrequencyMinutes=60, sensorTransmissionPowerLevel=power,
        )

    # -- enqueue --------------------------------------------------------------

    def test_activate_enqueues_a_pending_command(self):
        response = self.client.patch("/api/channel/1/activate", **_auth(self.key))

        self.assertEqual(response.status_code, 202)
        command = ManualCommand.objects.get(pk=response.json()["commandId"])
        self.assertEqual((command.channel_id, command.action, command.status),
                         (1, "activate", "pending"))

    def test_disabled_channel_is_not_acceptable(self):
        response = self.client.patch("/api/channel/2/activate", **_auth(self.key))

        self.assertEqual(response.status_code, 406)
        self.assertFalse(ManualCommand.objects.exists())

    def test_unknown_channel_is_not_found(self):
        response = self.client.patch("/api/channel/99/activate", **_auth(self.key))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ManualCommand.objects.exists())

    def test_unknown_action_is_bad_request(self):
        response = self.client.patch("/api/channel/1/wiggle", **_auth(self.key))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ManualCommand.objects.exists())

    # -- pending list (polled by the core) -----------------------------------

    def test_pending_list_exposes_channel_type_and_age(self):
        ManualCommand.objects.create(channel=self.enabledChannel, action="activate")

        response = self.client.get("/api/manualCommand/pending", **_auth(self.key))

        self.assertEqual(response.status_code, 200)
        commands = response.json()["manualCommands"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["channel"], 1)
        self.assertEqual(commands[0]["channelType"], "valve")
        self.assertGreaterEqual(commands[0]["ageSeconds"], 0)

    # -- result write-back (written by the core, polled by the UI) -----------

    def test_reporting_result_sets_terminal_status_and_clears_pending(self):
        command = ManualCommand.objects.create(channel=self.enabledChannel, action="activate")

        response = self.client.patch(
            f"/api/manualCommand/{command.id}",
            data={"status": "rejected", "message": "another channel is already active"},
            content_type="application/json",
            **_auth(self.key),
        )

        self.assertEqual(response.status_code, 200)
        command.refresh_from_db()
        self.assertEqual(command.status, "rejected")
        self.assertIsNotNone(command.processedAt)

        pending = self.client.get("/api/manualCommand/pending", **_auth(self.key)).json()
        self.assertEqual(pending["manualCommands"], [])

    def test_reporting_invalid_status_is_rejected(self):
        command = ManualCommand.objects.create(channel=self.enabledChannel, action="activate")

        response = self.client.patch(
            f"/api/manualCommand/{command.id}",
            data={"status": "banana"},
            content_type="application/json",
            **_auth(self.key),
        )

        self.assertEqual(response.status_code, 400)
        command.refresh_from_db()
        self.assertEqual(command.status, "pending")  # left untouched on a bad write
