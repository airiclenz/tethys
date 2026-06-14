# =============================================================================
# Pure silent-phase window evaluation.
#
# Kept dependency-free (stdlib only -- no Django imports) so the timezone math
# that gates ALL watering is unit-testable in isolation. `common.py` wraps this
# with the ORM query and the cached SILENT_PHASE state.
#
# A silent schedule's startTime is a wall-clock TIME-OF-DAY (e.g. 22:00) that the
# user configured and the web UI shows. It is stored as a DateTimeField on a
# placeholder date (1900-01-01, even 0001-01-01) in UTC, so its UTC clock-face is
# that time-of-day. We read that clock-face and re-anchor it on today's date in
# the comparison timezone, then compare against `now` there.
#
# Do NOT astimezone() the stored value across its placeholder date: a historical
# date's UTC offset differs from today's (Stockholm was +01:00 in 1900 vs +02:00
# in summer today), which would silently shift the window by an hour. (The older
# code had a different mismatch: a naive UTC-derived window vs a naive local
# clock.)
# =============================================================================

from datetime import datetime, timedelta, timezone


# =============================================================================
def evaluate_silent_phase(schedules, now):
    """
    Decide whether `now` falls inside a silent (quiet-hours) window.

    `now` must be timezone-aware; all comparisons happen in its timezone.
    `schedules` is an iterable of objects with:
      - `weekday`        : English day name ("Monday" ...) the window starts on
      - `startTime`      : a datetime stored in UTC whose UTC clock-face is the
                           wall-clock time-of-day the window starts at
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

        # Read the configured time-of-day from the stored UTC clock-face and
        # re-anchor it on the relevant date in the comparison timezone (see the
        # module header for why we do not astimezone() across the stored date).
        time_of_day = schedule.startTime.astimezone(timezone.utc)
        base_date = today if is_today else yesterday

        start_time = datetime(
            base_date.year,
            base_date.month,
            base_date.day,
            time_of_day.hour,
            time_of_day.minute,
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
