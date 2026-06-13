# 2026-06-13 — 02 — Silent-phase icon still not showing

**Focus for next session:** the web UI silent-phase icon still does not appear,
even though the silent-phase *calculation* is now correct.

---

## ✅ RESOLVED (2026-06-13)

The icon now shows. Two parts to the fix:

1. **The code fix (as recommended below).** `web/tethys_web/tools.py` →
   `getReponseForSystemStatus()` no longer returns the hardcoded stub. A new
   helper `getSilentPhaseStatus()` fetches the live status from the API
   (`GET silentPhaseStatus/<IANA-id>` with `settings.API_AUTH_HEADERS`),
   mirroring the `jobs.py` pattern, and falls back to `inPhase: False` on
   non-200 / connection error. Verified live: returns `inPhase: True`, window
   22:00–07:00. (Committed in `f668318`.)

2. **The real "still not showing" gotcha — restart the RIGHT service.** The
   `silentPhaseStatus` payload reaches the browser over the **websocket**, and
   the websocket consumer (`consumers.py` via `tethys_web.asgi:application`) runs
   under **`daphne.service`** (ASGI, port 8001) — *not* `tethys-web` (gunicorn,
   WSGI, port 8000, which only serves the HTTP pages). Restarting `tethys-web`
   alone left daphne running the old stubbed code, so the icon stayed hidden.
   **Fix: restart `daphne.service` as well** (or just use
   `install/services-restart.sh`, which restarts everything).

   → **Lesson for any future `web/` Python change that touches the websocket
   path: restart both `tethys-web` AND `daphne`.** The served static JS was
   confirmed identical to the repo (`/var/www/tethys/staticcollect`), so no
   `deploy-static.sh` was needed here.

---

## TL;DR — root cause (high confidence)

`web/tethys_web/tools.py` → `getReponseForSystemStatus()` (lines ~80–90) returns
a **hardcoded stub** for the silent-phase status:

```python
"silentPhaseStatus": {
    "lastCalculationTime": "1900-01-01T00:00:00Z",
    "startTime":           "1900-01-01T00:00:00Z",
    "endTime":             "1900-01-01T00:00:00Z",
    "inPhase": False           # <-- always False, never queries the API
}
```

This is the payload that actually drives the icon, so the icon is hidden no
matter the real state. The API itself is correct (verified live:
`inPhase: true`, window `22:00:00+02:00`–`07:00:00+02:00`).

## The display path (so the fix lands in the right place)

1. Frontend `web/static/ts/websocket.ts:56-58` — on connect calls
   `requestSystemStatus()`, then repeats every 30 s.
2. `web/tethys_web/consumers.py:51-52` — handles `requestSystemStatus` by calling
   `tools.getReponseForSystemStatus()`.
3. That response carries `silentPhaseStatus`; `websocket.ts:121-124` feeds it to
   `tethys.setSilentPhaseStatus(data.silentPhaseStatus)`.
4. `web/static/ts/common.ts:185-208` (`updateSilentPhaseStatus`) sets
   `#idIsSilentPhase` visibility from `silentPhaseStatus.inPhase` (template:
   `web/templates/layout.html:47`, default `visibility:hidden`).

Note: the `jobs.py` poll (which *does* fetch the real status and even logs
"Update found") only broadcasts `channelSummary` + `scheduleSummary` — it does
**not** send the system-status payload. So the stub in step 2 is the only thing
the icon ever sees.

## Recommended fix

Make `getReponseForSystemStatus()` fetch the live status from the API instead of
returning the stub. Mirror the working pattern already in
`web/tethys_web/jobs.py:67-84`:

- Build the IANA identifier from the local zone:
  `str(timeZoneLocal.get_localzone()).replace('/', '-')` (jobs.py:67-68).
- `requests.get(settings.API_URL + "silentPhaseStatus/" + ident,
  headers=settings.API_AUTH_HEADERS)` — **the key header is required now** (reads
  are gated by `ApiKeyRequired`; `settings.API_AUTH_HEADERS` already exists).
- Return the parsed JSON as `silentPhaseStatus` (it already has the right shape:
  `lastCalculationTime/startTime/endTime/inPhase`).
- Guard failures (non-200 / unreachable) — fall back to `inPhase: False` so the
  status panel still renders.

This is a `web/` TypeScript-free change (Python only), so **no `deploy-static.sh`
needed** — just restart `tethys-web` (`install/services-restart.sh` restarts
everything, or `sudo systemctl restart tethys-web.service`).

## How to verify

- Live API (needs the key; read from `globals/secrets.py`, do not paste it):
  `curl -s -H "X-API-Key: $KEY" http://localhost:5000/api/silentPhaseStatus/Europe-Stockholm`
  → currently `inPhase:true` between 22:00 and 07:00.
- After the fix, open/reload the web UI: the icon (`#idIsSilentPhase`) should
  become visible within the 30 s `requestSystemStatus` interval (immediate on
  page load/connect). The browser console logs "Send command requestSystemStatus".
- Optional: a unit test for `getReponseForSystemStatus()` with the API call
  mocked (assert it surfaces `inPhase` and falls back on error).

## State / important caveats

- **Nothing is committed this session.** The silent-phase + LAST_DATA_UPDATE work
  (prior turns) and the time-of-day fix below are all **uncommitted** in the
  working tree, intermixed with the user's in-flight *remote-access hardening*
  changes (`settings.py`, `web/.../settings.py`, `views.py`, `CHANGELOG.md`,
  `permissions.py`, `jobs.py`, etc.). Decide commit-splitting with the user
  before committing — several files contain both workstreams.
- This session's silent-phase changes (details in `CHANGELOG.md` →
  "Silent-phase watering gate fix" section, do not duplicate here):
  - `api/tethys_api/silentphase.py` — treats `startTime` as a wall-clock
    time-of-day; reads the stored **UTC clock-face** and re-anchors on today in
    the comparison zone. Fixed an earlier 1-hour shift caused by `astimezone()`
    across the schedule's 1900 placeholder date (historical offset).
  - `api/tethys_api/settings.py` — API Django `TIME_ZONE` reverted to `'UTC'`
    (storage zone). Deployment/display zone stays `globals/config.py`
    (`Europe/Stockholm`), used by `core`/`web`.
  - Tests updated: `api/tethys_api/tests/test_silentphase.py` (8 tests).
- **Only `tethys-api` was restarted** this session. The web fix will need a
  `tethys-web` restart.
- **Reads now require `X-API-Key`** (`ApiKeyRequired`); only `OPTIONS` is exempt.
  Any new server-side API call from `web/` must send `settings.API_AUTH_HEADERS`.
- Tests currently green: 32 core (`pytest` from `code/master/`, via
  `env_tethys/bin/python`), 22 API (`python manage.py test tethys_api` from
  `code/master/api/`). `pytest` was pip-installed into `env_tethys` (dev dep).
- Services run **in place from the repo** (no copy step for Python); static
  assets are the exception (copied to `/var/www/tethys/staticcollect`).
- Data note: the 7 silent schedules are stored as `22:00` UTC, `durationMinutes
  540` (→ 07:00), weekdays Mon–Sun; one row (id 3) has a `0001-01-01` placeholder
  date with a weird LMT offset — the time-of-day fix handles it.

## Suggested skills

- **`verify`** / **`run`** — confirm the icon shows in the running web UI after
  the fix (this is a UI-observable behavior, not just a unit test).
- **`feature-implementation`** — scope the `getReponseForSystemStatus()` change
  with a self-review checklist.
- **`code-review`** — quick pass once done, focused on the web→API read path and
  the key header.
- **`pr-lifecycle`** — when ready to commit/split the intermingled workstreams.
