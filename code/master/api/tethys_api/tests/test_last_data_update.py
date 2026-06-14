# =============================================================================
# Tests for the LAST_DATA_UPDATE wiring.
#
# Regression for the module-global aliasing bug: the writer
# (views.setLastDataUpdateNow) used `global` on a name imported via
# `from .globals import LAST_DATA_UPDATE as ...`, so it only rebound the views
# module's copy. The canonical globals.LAST_DATA_UPDATE -- the value common.py's
# silent-phase recalc trigger reads -- was never updated and stayed datetime.min.
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

from datetime import datetime

from django.conf import settings
from django.test import TestCase

from tethys_api import globals as appGlobals
from tethys_api.globals import setLastDataUpdate, getLastDataUpdate


def _auth(key):
    return {"HTTP_X_API_KEY": key}


class LastDataUpdateWiringTests(TestCase):

    def setUp(self):
        # The canonical store is process-global mutable state; reset per test.
        appGlobals.LAST_DATA_UPDATE = datetime.min

    def test_setter_mutates_canonical_store_through_alias(self):
        # setLastDataUpdate is imported here under a local name -- exactly the
        # situation the old code got wrong. Calling it must still update the
        # single canonical value that getLastDataUpdate / common.py observe.
        self.assertEqual(appGlobals.LAST_DATA_UPDATE, datetime.min)
        setLastDataUpdate()
        self.assertNotEqual(appGlobals.LAST_DATA_UPDATE, datetime.min)
        self.assertEqual(getLastDataUpdate(), appGlobals.LAST_DATA_UPDATE)

    def test_mutating_request_bumps_canonical_timestamp(self):
        # End-to-end: a mutating endpoint (via views.setLastDataUpdateNow) must
        # reach the canonical store that the silent-phase trigger reads.
        self.assertEqual(getLastDataUpdate(), datetime.min)
        response = self.client.post(
            "/api/scheduleType/",
            data={"name": "silent"},
            content_type="application/json",
            **_auth(settings.TETHYS_API_KEY),
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(getLastDataUpdate(), datetime.min)
