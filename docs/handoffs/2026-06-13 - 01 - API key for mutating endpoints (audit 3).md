# Handoff — Tethys API key for mutating endpoints (audit #3)

**Date:** 2026-06-13
**Branch:** `fix/pump-control-safety-module` (same branch as phase 1; off `main`)
**Last commit:** `e002e1f` — work below is **uncommitted** in the working tree.
**Status:** Implemented + **verified live on the Pi**. NOT committed. NOT pushed.

> **Superseded (2026-06-13, remote-access hardening):** the "reads stay open"
> design below was tightened. The API key is now required on **every** request,
> reads included (only the CORS preflight `OPTIONS` is exempt), so the system can
> be reached over a VPN overlay without exposing sensor/channel data. The
> permission class was renamed `ApiKeyForWrite` → `ApiKeyRequired`, all read
> callers (web UI, core, web backend) now send the key, and `initializeDatabase`
> became a key-gated `POST`. See `docs/remote-access-hardening.md`.

---

## What this work is

The audit's **action-order #3 — "lock down the API"** (CRIT-Security in
`docs/audits/2026-06-11 CodeAudit.md`). Every API view was unauthenticated and
LAN-reachable, so any host could `PATCH /api/channel/<n>/activate` a pump (and,
with the still-deferred manual auto-off, leave it on), or create/delete channels,
schedules, and wipe data.

This adds a **single shared API key** gating **all mutating requests**
(POST/PUT/PATCH/DELETE). Reads (GET) stay open so the dashboard, polling, and the
core's GET reads are untouched. The web UI stores the key in localStorage and
sends it as `X-API-Key`; the core sends it on its two POSTs.

The approved plan is at `/home/airic/.claude/plans/mighty-baking-peach.md`.

## Decisions made with the user (not obvious from the diff)

1. **Scope = ALL mutating endpoints**, not just activate/deactivate (user chose
   the stronger option). Consequence: the **core** POSTs (sensor data, action
   logs) also carry the key.
2. **Key storage = git-ignored local file** `code/master/globals/secrets.py`
   (single source of truth read by BOTH the Django API and the non-Django core).
   `secrets.example.py` is the committed template. This also sets up the
   convention to move the Django `SECRET_KEY`s out of git later.
3. **Settings field is masked** (`type="password"`) and uses the existing
   `text-field` CSS class for a uniform look.

## How it works (the diff)

- **`globals/secrets.py`** (git-ignored) — `TETHYS_API_KEY`. Current deployed key:
  `hUPxXqsbp9nIsaeeb6lZbQfQTwv3KwSZ-Ore9LfzbMQ` (paste into web UI → Settings).
- **`api/tethys_api/permissions.py`** — `ApiKeyForWrite`: allows SAFE_METHODS
  (so GET + the CORS OPTIONS preflight pass), requires a constant-time-matching
  `X-API-Key` for mutating methods, fails closed.
- **`api/tethys_api/settings.py`** — adds `code/master` to `sys.path`, imports the
  key, sets `REST_FRAMEWORK` (`DEFAULT_PERMISSION_CLASSES` = the class,
  `DEFAULT_AUTHENTICATION_CLASSES = []` to avoid session/CSRF), and
  `CORS_ALLOW_HEADERS += x-api-key`.
- **`core/apiInterface.py` + `core/radio.py`** — send `X-API-Key` on the two core
  POSTs (actionLog, sensorData).
- **Web** — `common.ts` get/setApiKey (localStorage) + header injection into the 4
  mutating fetch wrappers; `channel.ts` shows a "set your API key" alert + reverts
  the toggle on 403; `layout.html` Settings popup + nav link.
- **`install/install.sh`** — generates `secrets.py` with a random key if missing
  (idempotent) and prints it; reminds again post-reboot. `install/readme.md`
  documents it.
- **`install/deploy-static.sh`** (NEW) — one-command frontend deploy: `tsc` then
  copy static → `/var/www/tethys/staticcollect` + chown. Tolerates tsc's non-zero
  exit (see TODO note) while keeping `set -e` for the copy steps.
- **`api/tethys_api/tests/test_api_key.py`** — 7 tests (GET open, OPTIONS open,
  activate/POST 403 without/wrong key, 2xx with key, hardware-not-touched-when-denied).

## Verified on the Pi (pumps/valves physically removed; LEDs on outputs)

- `python manage.py test tethys_api` → **7/7 pass**.
- Live curl: GET → 200 (no key); PATCH/PUT → **403** without/wrong key, **2xx**
  with key. **activate** drove GPIO16+6 HIGH (LED on), **deactivate** drove LOW.
- Core's real `createPumpActionInDB` with key → "successfully logged" (200);
  deleted the one test row afterwards (actionLog count restored to 142).
- Web serves the updated template + recompiled JS (via `deploy-static.sh`).
- Channel 1 was temporarily enabled for the LED test and **restored to disabled**
  (the state it was in — user had disabled channels when removing pumps).

## ⚠️ Working-tree caveats for whoever commits

1. **Recompiling regenerated ALL `.js`**, not just the two I changed. The diff
   shows `schedule.js`, `tool.js`, `websocket.js`, `templatter.js` (+ `.map`s) as
   modified — these are pure tsc re-emit artifacts (their `.ts` was untouched).
   **Recommendation:** keep only `common.js`/`channel.js` (+maps) and
   `git checkout` the four unrelated regenerated files to keep the diff focused —
   OR accept all as a consistent fresh build. Your call.
2. **`todo.txt` → `TODO.md`**: git shows `D todo.txt` + `?? TODO.md`. This rename
   is **pre-existing** (from an earlier session), not from this work. The new TS
   cleanup item was added to `TODO.md`. Decide whether to `git rm todo.txt` and
   `git add TODO.md` to make the rename explicit.
3. **`CHANGELOG.md`** (from the phase-1 session) is still untracked — the API-key
   work does NOT yet have a CHANGELOG entry. Add one when committing.
4. `globals/secrets.py` is correctly git-ignored (only `secrets.example.py` is
   tracked). Confirm it never gets committed.

## Deployment notes (easy to trip on)

- Web vhost is **`server_name tethys.local`** (plain `localhost` hits default
  nginx). Static is served from **`/var/www/tethys/staticcollect/`** via a plain
  `cp` (NOT Django collectstatic) — use `deploy-static.sh` after any `.ts` edit.
- The web app uses Django's **cached template loader**: template changes need a
  `systemctl restart tethys-web` (static/JS changes only need a browser reload).
- Restart services with `install/services-restart.sh`.

## Known limitations / still open (by design)

- **Plain HTTP on the LAN** → the key is sniffable. Raises the bar from "any LAN
  host" to "needs the key"; not transport security.
- **`initializeDatabase` is a state-changing GET**, so it stays open under the
  method-based scope (idempotent; the installer relies on it). Converting to POST
  is a follow-up.
- The audit's sibling quick wins — `DEBUG=False`, moving the Django `SECRET_KEY`s
  into `secrets.py` — are NOT done; the secrets-file convention is now in place
  for them.

## Next steps

1. **Commit** this work (resolve the caveats above) + add a `CHANGELOG.md` entry.
2. The branch now carries BOTH phase-1 (pump safety) and this (API key). Consider
   whether to split into separate PRs or land together.
3. Continue the audit order: **#4 silent-phase fix** (tz + type filter), **#5
   config consolidation**, then **#6 single GPIO owner / H-01** (= phase 2 of the
   pump work, which also gives the API manual-activate its auto-off and closes the
   last part of C-02).

## Suggested skills for the next session

- **`code-review`** — re-run on the branch before the PR.
- **`pr-lifecycle`** — push + open PR(s).
- **`verify`** / **`run`** — re-confirm on the Pi after any commit cleanup.
