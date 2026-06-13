# =============================================================================
# Pure silent-phase window evaluation.
#
# Kept dependency-free (stdlib only -- no Django imports) so the timezone math
# that gates ALL watering is unit-testable in isolation. `common.py` wraps this
# with the ORM query and the cached SILENT_PHASE state.
#
# The bug this fixes: the previous math built the window from a schedule's
# UTC-derived hour/minute as a *naive* datetime and compared it against the
# server's *naive local* clock, so the quiet-hours window was offset by the
# server's UTC<->local difference (and aware-vs-naive compares could TypeError).
# Here every comparison happens in the caller-supplied timezone.
# =============================================================================

from datetime import datetime, timedelta


# =============================================================================
def evaluate_silent_phase(schedules, now):
    """
    Decide whether `now` falls inside a silent (quiet-hours) window.

    `now` must be timezone-aware; all comparisons happen in its timezone.
    `schedules` is an iterable of objects with:
      - `weekday`        : English day name ("Monday" ...) the window starts on
      - `startTime`      : a datetime whose wall-clock time-of-day, read in
                           `now`'s timezone, is the window start
      - `durationMinutes`: window length in minutes

    A window whose weekday is *yesterday* is considered too, so a window that
    starts late and runs past midnight still suppresses watering after midnight.

    Returns `(inPhase, startTime, endTime)`:
      - when `inPhase` is True, the times bound the active window;
      - when False, they bound the next upcoming window *today* (or
        timezone-aware `datetime.max` sentinels if there is none).
    """

    tz = now.tzinfo
    today = now.date()
    yesterday = today - timedelta(days=1)

    start_time_next = datetime.max.replace(tzinfo=tz)
    end_time_next = datetime.max.replace(tzinfo=tz)

    for schedule in schedules:
        is_today = today.strftime("%A") == schedule.weekday
        is_yesterday = yesterday.strftime("%A") == schedule.weekday

        # only windows that start today or yesterday can be active right now
        if not (is_today or is_yesterday):
            continue

        # read the configured wall-clock time-of-day in the deployment timezone
        local_start = schedule.startTime.astimezone(tz)
        base_date = today if is_today else yesterday

        start_time = datetime(
            base_date.year,
            base_date.month,
            base_date.day,
            local_start.hour,
            local_start.minute,
            tzinfo=tz,
        )
        end_time = start_time + timedelta(minutes=schedule.durationMinutes)

        # are we inside this window right now?
        if start_time < now < end_time:
            return True, start_time, end_time

        # otherwise, track the soonest still-upcoming window today
        if is_today and now < start_time < start_time_next:
            start_time_next = start_time
            end_time_next = end_time

    return False, start_time_next, end_time_next
