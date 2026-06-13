# Tethys Code Audit — 2026-06-11

> Multi-agent code review handoff. A fresh agent can use this document to start
> fixing the findings without re-running the audit.

**Scope:** All source under `code/` — Python master (`api/`, `web/`, `core/`,
`globals/`, `watchdog/`), C++/Arduino sensor firmware (`sensor/src`,
`sensor/include`, `sensor/lib`), and the TypeScript frontend. Excluded:
`hardware/` PCB files, fonts, committed JS build artifacts (verified not stale).

**Mission (derived — no CLAUDE.md/ADRs exist):** Tethys is an unattended
wireless plant-watering system. A Raspberry Pi hub runs a Django REST API + web
UI plus a "core" process that drives an SPI radio and GPIO pumps; it talks to
battery-powered Arduino sensor/pump nodes that read soil moisture, drive pumps,
and deep-sleep to conserve battery.

**Files reviewed:** ~30 Python, ~20 C++, 7 TypeScript, plus Django/nginx/systemd
config.

**Reviewed at commit:** `9f3c1fe` (branch `main`).

---

## Executive Summary

The single most important finding: **the core process does not start.**
`code/master/core/tethys_core.py:49` calls `asyncio.create_task()` on a *plain
synchronous* function, raising `TypeError` at launch (flagged independently by
three specialists). As committed, automatic watering, radio handling, and fan
control never run.

Beyond that, two systemic safety/security gaps compound each other: **there is
no upper bound on pump-on time anywhere**, and **the REST API that drives the
pumps requires no authentication** and is reachable across the LAN — so any host
can turn a pump on and leave it on, flooding a plant. The "silent phase"
(quiet-hours) feature, which gates *all* watering, is doubly broken: it queries
the wrong set of schedules and compares timezone-mismatched datetimes. The
repository has **zero tests**, and an abandoned "globals" config refactor has
left three drifted copies of config (`TIME_ZONE` already divergent: UTC vs
Europe/Stockholm).

Good news: most fixes are concentrated and well-localized, and the underlying
design (separate core/API/web processes, sleeping battery nodes) is sound.

---

## Mission & Architecture Findings

### Critical

- **[C-01] `code/master/core/tethys_core.py:49` — core process crashes on
  startup.** `asyncio.create_task(handleCoreActivities())` is passed the return
  value of a *synchronous* `def handleCoreActivities` (line 39), not a coroutine
  → `TypeError: a coroutine was expected`, so `main()` dies and
  `task_fan = fan.control_fan()` is never scheduled. Even if it didn't raise, the
  function is an infinite blocking `while True` doing synchronous
  `requests`/`radio` I/O that would starve the fan coroutine. **Net effect: no
  watering, no radio, no PID fan control — the Pi can overheat.**
  *(Cross-validated ×3: Mission, Bug, Concurrency.)*
  **Fix:** make `handleCoreActivities` an `async def` looping with
  `await asyncio.sleep(...)`, and run the blocking radio/HTTP work via
  `asyncio.to_thread`.

- **[C-02] `code/master/core/actionEngine.py:60-85`, `channel.py:13-49`,
  `api/.../views.py:238-269` — no max-runtime or volume kill-switch on pumps.**
  `pumpDurationSeconds` is an unbounded `IntegerField` (models.py:59) used
  directly as the pump-on window, with no clamp and no try/finally guaranteeing
  the GPIO returns LOW. The manual `channel_single_action` "activate" path turns
  a pump ON with **no auto-off at all**. A bad config write, a hung
  `handleRadioEvents`, or an `activate` with no `deactivate` floods the plant.
  *(Cross-validated: Mission, Test-coverage.)*
  **Fix:** enforce a hard `MAX_PUMP_SECONDS` at model/serializer and in
  `actionEngine`; wrap pumping in try/finally that always drives the pin LOW;
  give manual activate a server-side auto-off timer.

### High

- **[H-01] `code/master/core/channel.py:28-47` vs `api/.../views.py:238-266` —
  two processes are independent owners of the same GPIO lines.** Both the core
  (automatic watering) and the Django API (manual activate) call
  `setOutputState`, which each time does its own `gpiochip_open(0)` →
  `gpio_claim_output` → write → close. The fan controller (`fanController.py:23`)
  holds its own separate chip handle too. With lgpio a line claimed by one
  handle/process can't be claimed by another; an interleaved
  manual-tap-during-auto-pump hits `lgpio.error` — which is **swallowed, and the
  function returns `True` anyway** (channel.py:45-47), so a failed *off*-write
  looks successful → valve stuck open. *(Cross-validated: Mission, Concurrency.)*
  **Fix:** route all GPIO through a single owner (the core) with one shared chip
  handle; have the API send a command to core rather than driving pins; never
  report success after a swallowed error.

### Medium

- **[M-01] `code/sensor/src/wpw_RXTX.cpp`, `wpw_Pumps.cpp`,
  `WirelessPlantWatering.cpp` — the firmware ships a complete rival watering
  controller under `#ifdef RX`.** A standalone receiver with OLED, buttons, 5
  valves + pump, its own moisture-trigger logic and config exchange — duplicating
  the Pi master's job, with its own divergent pump-timing. Two unsynchronized
  sources of truth for the most safety-critical behavior. *(uncertain — may be an
  intentional standalone variant, but nothing in-repo says so.)*
  **Fix:** document which hub is canonical; remove or clearly quarantine the RX
  build.

- **[M-02] `code/sensor/src/WirelessPlantWatering.cpp:84-104` — startup config
  handshake burns battery for ~16 min if the master is unreachable.** `setup()`
  retries `RequestConfiguration()` up to 1000× at ~1s each (radio powered, 200ms
  busy-wait), all **before the first `Sleep()`** — contradicting the "sleep to
  conserve power" goal.
  **Fix:** cap retries to a handful, fall back to EEPROM config + immediate
  sleep, retry opportunistically on later wakes.

---

## Critical & High Findings (other categories)

### Security

- **[CRIT] `api/.../views.py` (all views), `settings.py` (no `REST_FRAMEWORK`
  block) — unauthenticated API drives pumps and all data.** Every view is a bare
  `@api_view` with no `permission_classes`, and no DRF default is configured, so
  DRF falls back to `AllowAny`. `PATCH /api/channel/<n>/activate` directly drives
  the pump GPIO. The API nginx (`install/assets/tethys-api.nginx`) does
  `listen 5000;` (all interfaces).
  `curl -X PATCH http://tethys.local:5000/api/channel/1/activate` from any LAN
  host turns on a pump (and combined with [C-02], leaves it on); attackers can
  also create/delete channels and schedules and wipe sensor/action data.
  *(Cross-validated: Security, Mission, Test-coverage.)*
  **Fix:** set `REST_FRAMEWORK` defaults to `IsAuthenticated` + token auth; have
  the core authenticate with that token.

- **[HIGH] `api/.../settings.py:26`, `web/.../settings.py:25` — `DEBUG = True` on
  a network-exposed device.** Any triggered exception leaks full tracebacks,
  settings, SQL, and locals to remote callers (web served on `:80` to the whole
  LAN). **Fix:** `DEBUG = False` in production.

- **[HIGH] `api/.../settings.py:23`, `web/.../settings.py:22` — hardcoded Django
  `SECRET_KEY` committed to git.** With admin mounted at `/admin/` and
  session/CSRF signing keyed on this value, a reader of the repo can forge
  session cookies and signed values against a live instance.
  **Fix:** load from env/secret file; **rotate the leaked keys**; scrub history.

- **[HIGH] `sensor/include/wpw_Config.h:32-38` + `core/radio.py` —
  unauthenticated, unencrypted RF protocol with hardcoded pipe addresses.** A
  nearby attacker with a cheap nRF24 module can transmit on the fixed pipe
  address with `DATATYPE_SENSORDATA` and `MoistureLevel = 0%`; the master posts
  it straight to the API and the action engine treats the plant as dry →
  repeatable overwatering. Forged config packets can also tamper with calibration
  / drain batteries.
  **Fix:** add a per-device shared key with a MAC + rolling counter; randomize
  pipe addresses per deployment.

### Bugs / Logic

- **[CRIT/HIGH] `api/.../common.py:191-198` — `loadSilentSchedules()` ignores
  schedule type.** The docstring says "all schedules of type silent," but the
  query is `Schedule.objects.filter(enabled=True)` with **no `scheduleType`
  filter**. Any enabled schedule of any type becomes a quiet-hours window that
  suppresses watering (actionEngine.py:28-29 returns early).
  *(Cross-validated: Mission, Bug.)*
  **Fix:** `filter(enabled=True, scheduleType__name="silent")`.

- **[HIGH] `api/.../common.py:120-152` — silent-phase window compares mismatched
  time bases (the open `todo.txt` bug).** With `USE_TZ=True`/`TIME_ZONE='UTC'`,
  `schedule.startTime` is timezone-aware UTC, but the code rebuilds it as a
  **naive** datetime from its UTC `.hour/.minute` and compares against naive
  **local** `datetime.now()`. The window is offset by the server's UTC↔local
  difference (and aware-vs-naive comparisons can `TypeError`), so the system
  waters during the user's declared quiet hours. The passed `timeZoneIdentifier`
  is used only for printing.
  *(Cross-validated ×4: Mission, Bug, Health, Test-coverage.)*
  **Fix:** convert both `now` and the window into the same
  `ZoneInfo(timeZoneIdentifier)` before comparing; keep the midnight-wraparound
  (yesterday/today) branch.

- **[HIGH] `core/actionEngine.py:28-29` + `apiInterface.py:74-93` —
  `isInSilentPhase()` returns `None` on API error and is treated as "not silent"
  → fail-open watering.** When the API is unreachable, `if api.isInSilentPhase():
  return` falls through and the engine waters blind on possibly-stale state.
  *(Cross-validated: Bug, Test-coverage.)*
  **Fix:** `status = api.isInSilentPhase(); if status is None or status: return`
  (do not act when state is unknown).

- **[HIGH] `sensor/src/wpw_RXTX.cpp:91-92` — copy-paste bug strands the 6th
  sensor.** `openReadingPipe(5, pipes[5])` then `openReadingPipe(5, pipes[6])` —
  pipe index 5 is opened twice, so `pipes[6]` (the 6th sensor, explicitly added
  in recent commits) is never registered, and `HandleReceiver` rejects
  `pipeNo > 5`. Note nRF24 has only 6 reading pipes (0–5), so fitting 6 sensors +
  master needs an addressing rethink, not just a one-line fix.
  *(Cross-validated: Mission, Bug, Test-coverage.)*
  **Fix:** correct the pipe mapping, bump `SENSOR_COUNT`/`_sensors[]` to 6, relax
  the guard.

### Concurrency / Resource Safety

- **[HIGH] `web/tethys_web/jobs.py:21-33,116-119` — unbounded polling-timer thread
  leak.** `startPolling()` runs on every websocket `connect()`; the `RepeatTimer`
  is assigned to a *local* (`repeater`) while `global thread` names the wrong
  variable, so the thread reference is dropped and `.cancel()` can never be
  called. `disconnect()` stops nothing. One daemon timer hammers the API every
  10s forever, even with zero clients.
  **Fix:** store the timer on a module object, track connection count, cancel when
  the group empties.

- **[HIGH] `sensor/src/wpw_Input.cpp:15-16` — ISR-shared flags are non-`volatile`
  and updated non-atomically.** `_statusInput` / `_statusAcceleration` are written
  in button ISRs (attached `CHANGE`) and read/modified in the main loop as plain
  `uint8_t`. The compiler may cache them, and `setBit/deleteBit` is a
  read-modify-write that an interrupt can clobber mid-sequence → dropped/missed
  button edges.
  **Fix:** declare `volatile`; guard main-loop RMW with `ATOMIC_BLOCK`/`cli()`-`sei()`.

- **[HIGH] `sensor/src/wpw_Sleep.cpp:37-110` +
  `WirelessPlantWatering.cpp:201-204` — non-atomic sleep-enter and ignored wake
  flag.** The flag is cleared, then several statements run before `sleep_mode()`,
  and the loop unconditionally decrements its counter without re-checking
  `_watchdog_event` after waking. A consumed watchdog tick during setup can
  mistime the measurement interval.
  **Fix:** use the atomic
  `cli(); if(!ready){sleep_enable(); sei(); sleep_cpu(); sleep_disable();} sei();`
  idiom and only proceed when `_watchdog_event` is set.

- **[HIGH] `core/radio.py:155-215` — single radio stops listening during
  un-timed-out blocking HTTP.** `handlePayload` calls `stopListening()` then does
  blocking `requests.post` (and `sendConfig` does several blocking calls) before
  re-listening; with up to 6 sensors and a tiny nRF24 FIFO, packets are dropped,
  and with **no `timeout=` on any `requests` call** (here, `apiInterface.py`,
  `jobs.py`, `tools.py`) a hung API stalls the radio loop indefinitely.
  **Fix:** buffer the payload, `startListening()` immediately, POST after; add
  explicit timeouts everywhere.

---

## Medium Findings

- **[Bug] `sensor/src/wpw_Pumps.cpp:107-136` — `millis()` rollover in
  `DoPumping`.** `millis() < (startTime + duration)` mis-terminates across the
  ~49.7-day `millis()` wrap; the RX master never sleeps and runs `loop()`
  forever, so this is reachable. **Fix:** use `(millis() - startTime) < duration`.

- **[Bug] `core/radio.py:155-161` — `payload` can be referenced unbound.** It's
  only assigned inside `while self.radio.available():`; if the FIFO drains between
  the outer check and the loop, `handlePayload(pipeNo, payload)` raises
  `UnboundLocalError` and aborts the receive cycle. (Also shadows builtin `len`.)
  **Fix:** `payload = None` before the loop and bail if still None.

- **[Concurrency] `api/.../settings.py:89-90`, `web/.../settings.py:115-116` —
  SQLite without WAL/timeout under concurrent writers.** Gunicorn runs 3 workers
  (`api/config/gunicorn.py:4`) plus the core posting sensor/pump data; SQLite's
  single-writer lock yields `database is locked`. Note the api and web `BASE_DIR`s
  differ, so they may be writing *separate* db files — verify they're meant to
  share one. **Fix:** set `OPTIONS` with a `timeout` and
  `PRAGMA journal_mode=WAL`, or use one writer / a real DB.

- **[Health] Abandoned "globals" refactor → three drifted config copies.**
  `globals/config.py` was created (commit 1d03942) but only `version` is imported
  from it; `DATETIME_FORMAT`/`NO_MILL` are duplicated in `core/config.py`,
  `globals/config.py`, and `web/.../settings.py` with **zero importers** of the
  globals copies, while `core/*` still does `from config import *`. `TIME_ZONE`
  has **already diverged**: `Europe/Stockholm` in core/web vs `UTC` in
  `api/.../settings.py:119` — the root enabler of the silent-phase bug.
  **Fix:** finish the migration into one canonical module; delete the dupes.

- **[Health] Dead-code cluster (verified zero callers).** `lib/AsyncronousBlink/`
  (superseded by inline `wpw_Blinker`, and already diverged: array length 5 vs
  10); the Python presentation layer `web/.../tools.py`
  `formatChannelSummaries`/`getTransmissionPowerLabel`/`getTimePassedSinceString`
  (moved to `ts/tool.ts`); `core/apiInterface.py` `loadChannel` +
  `loadAllChannelSummaries` (the latter also broken — reads `"channelSummary/"`
  vs the API's `"channelSummaries"`); `core/radio.py:90-125` `setupInterrupt`
  (body is `pass` + commented-out alternatives); and the never-referenced
  `FLAG_HANDLER` singleton in `core/config.py:17`. **Fix:** delete.

- **[Concurrency + Health] `core/config.py` `FlagHandler` — inconsistent access +
  6-vs-5 channel mismatch.** `channelFlags` is set on the class in one place
  (`actionEngine.py:36`) and via throwaway instances elsewhere (`radio.py:206`,
  `actionEngine.py:33`); it only works because the list is a shared mutable class
  attribute. Separately, `FlagHandler` has 6 flags but `hardware.Pins.CHANNELS`
  has 5 entries (`hardware.py:13`), so a channel-6 flag → `IndexError` in
  `setOutputState`. **Fix:** one explicit singleton/module list; reconcile 6
  channels vs 5 GPIO pins.

- **[Bug] (uncertain — conflicting evidence) radio wire-format dual source of
  truth.** `core/radio.py` hand-maintains `struct.pack/unpack` formats that must
  match the C++ `Package`/`ConfigurationPackage` structs in `wpw_RXTX.h`. One
  specialist flagged the Python `float` offset (`data[2:6]`) as mismatched against
  a 4-byte-aligned C++ layout (float at offset 4); however, the sensor targets are
  **8-bit AVR (attiny84 / ATmega32u4), where struct alignment is 1 and there is no
  padding**, so the float sits at offset 2 and Python matches today. Treat the
  "active bug" claim as a false alarm *for the current AVR targets*, but the
  format is genuinely duplicated and unguarded. **Fix:** add a round-trip test
  pinning the exact byte layout, and a shared header / codegen before the format
  changes again or an aligned MCU is added. **Verify on the actual RX target
  before acting.**

---

## Cross-Validated Findings (highest confidence)

1. **Core won't start** (`tethys_core.py:49`) — Mission + Bug + Concurrency (×3).
2. **Silent-phase timezone bug** (`common.py:120-152`) — Mission + Bug + Health + Test (×4).
3. **Unauthenticated API drives pumps** — Security + Mission + Test.
4. **No pump max-runtime kill-switch** — Mission + Test.
5. **`loadSilentSchedules` ignores type** — Mission + Bug.
6. **6th-sensor pipe bug** (`wpw_RXTX.cpp:91-92`) — Mission + Bug + Test.
7. **Two GPIO owners / swallowed error returns True** — Mission + Concurrency.
8. **`isInSilentPhase()` None → fail-open** — Bug + Test.

---

## Recommended Action Order

1. **Make the core run** [C-01] — nothing else matters until the process boots.
   Verify on the Pi.
2. **Pump safety** [C-02] — clamp max runtime + try/finally off + manual auto-off.
   This is the flood guard.
3. **Lock down the API** [CRIT-Security] — add DRF auth/permissions; the unauth
   pump endpoint + no flood limit is the worst combination. Also flip
   `DEBUG=False` and move `SECRET_KEY` out of git (quick wins).
4. **Fix silent-phase** — the type filter and the timezone math together; both
   gate all watering. Do this alongside #5.
5. **Consolidate config** [Health] — finish the globals refactor so `TIME_ZONE`
   has one value; this unblocks a clean silent-phase fix.
6. **Single GPIO owner** [H-01] — needs a small design decision (API → core
   command path) before coding.
7. **Concurrency hygiene** — radio listen-window + request timeouts [H],
   polling-thread leak [H], SQLite WAL [M].
8. **Firmware** — 6th-sensor pipe [H], `volatile`/atomic ISR flags [H], sleep
   idiom [H], `millis()` rollover [M].
9. **Add the first tests** — start with the silent-phase window evaluator and the
   radio byte-layout round-trip; both would have caught active bugs.
10. **Sweep dead code** [Health] — cheap, low-risk, reduces confusion.

---

## What Looked Good

The process decomposition is sensible — a hardware-owning core, a Django API as
the data store, a web/websocket UI, and a watchdog — and the battery-node design
(watchdog-driven wake, deep sleep, EEPROM-persisted config) is the right shape
for the power budget. The TypeScript frontend is cleanly separated and its
committed build artifacts were verified *not* stale. Also debunked a
scary-looking lead: the `/shutdown` "Order 66" UI link
(`web/templates/layout.html:81`) is a dead link with no backend route, not an
exploitable shutdown endpoint. Once core-startup and pump-safety are addressed,
this is a solid, fixable codebase — the problems are concentrated, not pervasive.

---

## State / Notes for the Next Agent

- **No test infrastructure exists.** `find code -iname '*test*'` returns nothing;
  `code/sensor/.travis.yml` is entirely commented-out PlatformIO boilerplate (runs
  nothing). Any fix should land with its first test.
- **No CLAUDE.md / ADRs.** The mission above is derived from code + `todo.txt`;
  confirm with the maintainer before treating it as authoritative.
- `todo.txt` at repo root already records the silent-phase timezone bug.
- Working tree was clean at audit time (commit `9f3c1fe`, branch `main`).

## Suggested Skills

- **`coding-standards`** — apply when writing the fixes (error handling, security
  patterns, test structure).
- **`feature-implementation`** — for tackling individual findings as scoped units
  of work with a self-review checklist.
- **`verify`** / **`run`** — to confirm the core actually boots on the Pi after
  fixing [C-01], and that pump activation behaves after the safety/auth fixes.
- **`pr-lifecycle`** — to open PRs per fix cluster following the action order.
- **`code-review`** — re-run after fixes to confirm the cross-validated findings
  are resolved.
