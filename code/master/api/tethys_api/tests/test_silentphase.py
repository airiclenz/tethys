# =============================================================================
# Tests for the silent-phase (quiet-hours) watering gate.
#
#   * evaluate_silent_phase: the pure, timezone-aware window math (no DB).
#   * loadSilentSchedules:   only enabled schedules of type "silent" count.
#
# These would have caught the audited bug: the old math compared a naive
# UTC-derived window against the server's naive local clock, so the window was
# offset by the UTC<->local difference; and loadSilentSchedules ignored the
# schedule type, so ANY enabled schedule suppressed watering.
#
# Run from code/master/api/:  python manage.py test tethys_api
# =============================================================================

import unittest
from collections import namedtuple
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase

from tethys_api.models import Schedule, ScheduleType
from tethys_api.silentphase import evaluate_silent_phase


TZ = ZoneInfo("Europe/Stockholm")

# A stand-in for a Schedule row carrying just the fields the evaluator reads.
FakeSchedule = namedtuple("FakeSchedule", ["weekday", "startTime", "durationMinutes"])


def _at(year, month, day, hour, minute, tz=TZ):
    return datetime(year, month, day, hour, minute, tzinfo=tz)


class EvaluateSilentPhaseTests(unittest.TestCase):
    '''Pure window math -- no Django DB needed.'''

    def test_now_inside_window_is_silent(self):
        now = _at(2026, 6, 12, 22, 30)  # a Friday, 22:30 local
        sched = FakeSchedule(now.strftime("%A"), _at(2026, 6, 12, 22, 0), 120)
        inPhase, start, end = evaluate_silent_phase([sched], now)
        self.assertTrue(inPhase)
        self.assertEqual(start, _at(2026, 6, 12, 22, 0))
        self.assertEqual(end, _at(2026, 6, 13, 0, 0))

    def test_now_before_window_is_not_silent_and_reports_next(self):
        now = _at(2026, 6, 12, 21, 0)
        sched = FakeSchedule(now.strftime("%A"), _at(2026, 6, 12, 22, 0), 60)
        inPhase, start, end = evaluate_silent_phase([sched], now)
        self.assertFalse(inPhase)
        self.assertEqual(start, _at(2026, 6, 12, 22, 0))  # the upcoming window

    def test_now_after_window_is_not_silent(self):
        now = _at(2026, 6, 12, 23, 30)
        sched = FakeSchedule(now.strftime("%A"), _at(2026, 6, 12, 22, 0), 60)  # ends 23:00
        inPhase, _start, _end = evaluate_silent_phase([sched], now)
        self.assertFalse(inPhase)

    def test_window_started_yesterday_still_silent_after_midnight(self):
        now = _at(2026, 6, 13, 0, 30)  # 00:30, just past midnight
        yesterday = now - timedelta(days=1)
        # window starts yesterday 23:00, runs 120 min -> ends today 01:00
        sched = FakeSchedule(yesterday.strftime("%A"), _at(2026, 6, 12, 23, 0), 120)
        inPhase, _start, _end = evaluate_silent_phase([sched], now)
        self.assertTrue(inPhase)

    def test_other_weekday_is_ignored(self):
        now = _at(2026, 6, 12, 22, 30)
        other = (now + timedelta(days=2)).strftime("%A")  # not today, not yesterday
        sched = FakeSchedule(other, _at(2026, 6, 12, 22, 0), 120)
        inPhase, start, _end = evaluate_silent_phase([sched], now)
        self.assertFalse(inPhase)
        self.assertEqual(start, datetime.max.replace(tzinfo=TZ))  # no upcoming window

    def test_utc_stored_time_is_localized_before_compare(self):
        # The DB stores schedule times timezone-aware in UTC. In summer Stockholm
        # is UTC+2, so a 22:00 local window is stored as 20:00 UTC. The evaluator
        # must localize it back to 22:00 local -- this is exactly the offset the
        # old naive math got wrong.
        now = _at(2026, 6, 12, 22, 30)
        start_utc = datetime(2026, 6, 12, 20, 0, tzinfo=ZoneInfo("UTC"))  # == 22:00 local
        sched = FakeSchedule(now.strftime("%A"), start_utc, 120)
        inPhase, start, _end = evaluate_silent_phase([sched], now)
        self.assertTrue(inPhase)
        self.assertEqual(start, _at(2026, 6, 12, 22, 0))


class LoadSilentSchedulesTests(TestCase):
    '''loadSilentSchedules must return only enabled schedules of type silent.'''

    @classmethod
    def setUpTestData(cls):
        cls.silent = ScheduleType.objects.create(name="silent")
        cls.other = ScheduleType.objects.create(name="watering")

        # an enabled silent schedule -- should be returned
        Schedule.objects.create(
            enabled=True, weekday="Monday", scheduleType=cls.silent,
            startTime=datetime(2026, 6, 12, 22, 0, tzinfo=ZoneInfo("UTC")),
            durationMinutes=60,
        )
        # an enabled NON-silent schedule -- must NOT be returned (the audited bug)
        Schedule.objects.create(
            enabled=True, weekday="Monday", scheduleType=cls.other,
            startTime=datetime(2026, 6, 12, 8, 0, tzinfo=ZoneInfo("UTC")),
            durationMinutes=60,
        )
        # a disabled silent schedule -- must NOT be returned
        Schedule.objects.create(
            enabled=False, weekday="Tuesday", scheduleType=cls.silent,
            startTime=datetime(2026, 6, 12, 22, 0, tzinfo=ZoneInfo("UTC")),
            durationMinutes=60,
        )

    def test_only_enabled_silent_schedules_returned(self):
        from tethys_api.common import loadSilentSchedules
        result = list(loadSilentSchedules())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].scheduleType.name, "silent")
        self.assertTrue(result[0].enabled)
