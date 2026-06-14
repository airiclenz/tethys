# Changelog

All notable changes to Tethys are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Current released version: **2.0.0** (`code/master/globals/config.py`).

---

## [Unreleased]

### Remote-access hardening (prerequisite for safe VPN access)

> Branch `fix/pump-control-safety-module` (2026-06-13). Hardens the app so it can
> be reached from outside the LAN over an encrypted overlay (Tailscale/WireGuard)
> **without** opening the LAN to the internet. The transport itself is operator
> setup, not code. See `docs/remote-access-hardening.md`.

#### Added
- **`docs/remote-access-hardening.md`** — the env vars, secrets, installer flags,
  the read-now-needs-key behavior, and a Tailscale setup pointer.
- **`globals/secrets.example.py`** — now also documents `API_SECRET_KEY` /
  `WEB_SECRET_KEY` (the Django secret keys, moved out of `settings.py`).
- **`api/tethys_api/tests/test_api_key.py`** — extended for the new posture: reads
  are denied without the key (403) and allowed with it (200); `initializeDatabase`
  is denied on unauthenticated GET (403), method-not-allowed on keyed GET (405),
  denied on keyless POST (403), and allowed on keyed POST.

#### Changed
- **`api/tethys_api/settings.py`, `web/tethys_web/settings.py`** — `DEBUG` now
  reads `TETHYS_DEBUG` (off by default); `SECRET_KEY` reads from the git-ignored
  `globals/secrets.py`; `ALLOWED_HOSTS` appends `TETHYS_ALLOWED_HOSTS`. The web
  settings also exposes `API_AUTH_HEADERS` for its server-side polling.
- **`api/tethys_api/permissions.py`** — `ApiKeyForWrite` → **`ApiKeyRequired`**:
  every request now needs `X-API-Key`, reads included; only `OPTIONS` (CORS
  preflight) is exempt.
- **Read callers now send the key** — the web UI `getCall` (`common.ts`), the core
  daemon (`apiInterface.py`, `radio.py`), and the web backend's server-side polls
  (`jobs.py`, `tools.py`).
- **`api/tethys_api/views.py`** — `initializeDatabase` is now a key-gated `POST`
  (was an open `GET`); `install.sh` calls it via authenticated `POST`.
- **`install/install.sh`, `installServices.sh`** — production-safe `DEBUG` default;
  new `--allowed-hosts` flag; generate `API_SECRET_KEY` / `WEB_SECRET_KEY` (and
  append them to pre-existing `secrets.py` on upgrade); inject `TETHYS_DEBUG` /
  `TETHYS_ALLOWED_HOSTS` into the systemd units.

#### Security
- Sensor data and channel state are no longer readable by anything that merely
  reaches the port; the worst-case (turning on a pump unauthenticated) remains
  closed. Combined with a VPN overlay, this enables remote access with no inbound
  ports and encrypted transport.

### Silent-phase watering gate fix (audit action items #4, #5, #8)

> Branch `fix/pump-control-safety-module` (2026-06-13). Fixes the quiet-hours
> ("silent phase") gate that suppresses **all** watering. Source:
> `docs/audits/2026-06-11 CodeAudit.md` (the silent-phase timezone bug —
> cross-validated ×4 — plus the `loadSilentSchedules` type filter, the fail-open
> `isInSilentPhase()`, and the divergent `TIME_ZONE` config that enabled them).

#### Added
- **`api/tethys_api/silentphase.py`** — `evaluate_silent_phase(schedules, now)`:
  a dependency-free (stdlib only) timezone-aware window evaluator extracted so
  the math that gates all watering is unit-testable without Django. `common.py`
  is now a thin wrapper (ORM query + cached `SILENT_PHASE` state) over it.
- **`api/tethys_api/globals.py`** — `setLastDataUpdate()` / `getLastDataUpdate()`
  helpers so the `LAST_DATA_UPDATE` timestamp is read/written through one
  canonical module global (see the fix below).
- **`api/tethys_api/tests/test_silentphase.py`** — 8 tests: 7 window-math cases
  (inside / before / after a window, the real 22:00→07:00 window, post-midnight
  wraparound, wrong weekday, and that the stored time-of-day is not shifted by
  the placeholder date's historical UTC offset), plus that `loadSilentSchedules`
  returns only enabled schedules of type `silent`.
- **`api/tethys_api/tests/test_last_data_update.py`** — 2 tests pinning the
  `LAST_DATA_UPDATE` wiring (setter mutates the canonical value through an
  alias; a mutating request bumps it).
- **`core/tests/test_action_engine.py`** — 3 tests pinning the fail-closed gate
  (unknown → skip and keep the flag; in-phase → skip; not-silent → evaluate).

#### Changed
- **`globals/config.py`** — single source of truth for the deployment/display
  `TIME_ZONE` (`Europe/Stockholm`), imported by `core/config.py` (the identifier
  the core passes to `silentPhaseStatus`) and the `web` Django settings. The
  **API keeps its Django `TIME_ZONE = 'UTC'`** as its storage zone — schedule
  start times are wall-clock times-of-day, so storing in UTC preserves the
  entered clock-face; the deployment zone is applied at silent-phase evaluation.
- **`api/tethys_api/common.py`** — `refreshSilentPhaseStatus` does all
  comparisons in the caller-supplied timezone (`datetime.now(tz)`), delegating
  the window math to `evaluate_silent_phase`; the cached `SILENT_PHASE`
  timestamps are now timezone-aware.
- **`core/actionEngine.py`** — the silent-phase check is now fail-closed.
- **`api/tethys_api/views.py`** — `setLastDataUpdateNow` / the `lastUpdate`
  endpoint go through the new `globals` helpers instead of a `from import`-aliased
  name (the `lastUpdate` web-polling wire format is unchanged).

#### Fixed
- **[Audit #4] `loadSilentSchedules()` ignored the schedule type** — it returned
  every enabled schedule (`filter(enabled=True)`), so any enabled schedule of any
  type became a quiet-hours window suppressing watering. Now filtered to
  `scheduleType__name="silent"`, matching its docstring.
- **[Audit #4] silent-phase window compared mismatched time bases** — the window
  was rebuilt as a *naive* datetime from a schedule's UTC `.hour/.minute` and
  compared against the server's *naive local* `datetime.now()`, offsetting the
  window by the server's UTC↔local difference (and aware-vs-naive compares could
  `TypeError`). Both sides are now timezone-aware in the configured zone.
- **[Audit #5] divergent `TIME_ZONE`** — `core`/`web` now share one
  deployment-zone definition (`globals/config.py`). The API deliberately keeps a
  `UTC` storage zone (see below); the previous divergence was a bug only because
  the old window math mishandled it.
- **silent-phase window shifted by an hour (icon failed to appear)** — schedule
  start times are wall-clock times-of-day stored on a placeholder date
  (`1900-01-01`). The evaluator localized that value with `astimezone()`, which
  uses the *placeholder date's* historical UTC offset (Stockholm was `+01:00` in
  1900 vs `+02:00` in summer today), shifting a 22:00 window to 23:00 — so at
  22:30 the gate read "not silent" and the UI icon stayed hidden while the
  schedule UI still showed 22:00–07:00. The evaluator now reads the stored UTC
  clock-face as the time-of-day and re-anchors it on today's date in the
  comparison zone (no cross-date `astimezone`).
- **[Audit #8] `isInSilentPhase()` → `None` was treated as "not silent"
  (fail-open)** — when the API is unreachable the engine watered blind. It now
  fails closed: an unknown status skips watering for that pass.
- **`LAST_DATA_UPDATE` never reached `common.py`** — `views.setLastDataUpdateNow`
  rebound a `from import`-aliased copy, so the canonical `globals.LAST_DATA_UPDATE`
  stayed `datetime.min` and the silent-phase "data update" recalc trigger never
  fired (an edited/added/removed schedule was only picked up at the next window
  boundary). Reads/writes now share one value via the `globals` helpers, and the
  recalc comparison localizes the naive timestamp to compare against the
  timezone-aware last-calculation time.

### Communication-protocol hardening

> Branch `fix/pump-control-safety-module` (2026-06-13). Makes the nRF24 link
> between the sensor nodes and the Pi master more robust (owner-reported
> unreliability). Source: `docs/audits/2026-06-13 - ProtocolReview.md` (findings
> P-01..P-07).

#### Added
- **`core/protocol.py`** — dependency-free (stdlib `struct` only) wire-format
  layer: versioned, fixed-size framing with validate-don't-raise parsing
  (`message_type`, `parse_sensor_reading`, `build_config_payload`), channel↔pipe
  mapping, and a `ConfigCache`. `radio.py` is now a thin driver over it, so the
  framing rules are unit-testable without `pyrf24`/`numpy`/GPIO.
- **`core/tests/test_protocol.py`** — 9 tests (battery-alert parsed, malformed
  frames never raise, version drop, config round-trip, pinned wire sizes,
  channel↔pipe mapping, config cache).
- **Versioned wire format** — a leading `ProtocolVersion` byte on both message
  structs, `__attribute__((packed))` + `static_assert` size checks in
  `sensor/include/wpw_RXTX.h`, and `PROTOCOL_VERSION` / `PAYLOAD_SIZE` constants
  in `wpw_Config.h`, mirrored by the Python `struct` formats.

#### Changed
- **`core/radio.py`** — answers `GETCONFIG` from an in-memory `ConfigCache`
  (warmed by `refreshConfigCache`) instead of a blocking HTTP GET inside the
  sensor's listen window; reads a fixed `PAYLOAD_SIZE` (no `getDynamicPayloadSize`
  with dynamic payloads disabled); reserves pipe 0 and maps channels 1:1 onto
  reading pipes 1..N; drains the whole RX FIFO; `setPayloadSize`/`setRetries`;
  per-call HTTP `REQUEST_TIMEOUT`.
- **`core/tethys_core.py`** — warms the config cache at startup and once per core
  loop pass (out of the radio response window).
- **`sensor/src/wpw_RXTX.cpp`** — `setPayloadSize`/`setRetries`, version byte on
  every outbound frame, version check on the received config, config-reply
  timeout 200 ms → 500 ms.
- **`sensor/src/WirelessPlantWatering.cpp`** — boot config handshake is now a
  bounded 5 retries with linear backoff that falls back to the EEPROM-cached
  config (was up to 1000× at 1 s, draining battery).

#### Fixed
- **[P-01]** master silently discarded a sensor's whole reading on a low battery
  (`DATATYPE_SENSORDATA_BATTERYALERT` matched no dispatch branch); both data
  types now save, and the alert is parsed + logged.
- **[P-02]** master read an undefined dynamic payload size (could flush the RX
  FIFO) while dynamic payloads were disabled — now a fixed payload size.
- **[P-03]** racy config handshake + boot retry storm (cache-served reply + a
  500 ms window + bounded backoff with EEPROM fallback).
- **[P-04]** a short/garbage frame raised an unhandled exception in the radio
  loop — parsing now validates length+version and never raises;
  `handlePayload` always resumes listening.
- **[P-05/06/07]** fragile unversioned struct layout, sensor bound to pipe 0, and
  FIFO drain that kept only the last frame.

#### Known limitations / coordinated flash
- **Not backward-compatible:** the version byte + fixed 8-byte payload mean the
  master and every sensor must be flashed together. A node on old firmware uses
  the 32-byte default payload → CRC mismatch → no ACK → it goes dark (clean, not
  corrupting; any stray frame is dropped by the version check). A length-based
  compatibility mode is possible if a phased rollout is ever needed.
- The low-battery **flag is not yet persisted** (`SensorData` has no column); the
  saved voltage carries the signal and the alert is logged. Tracked in `TODO.md`.
- The legacy Arduino `#ifdef RX` firmware receiver is untouched (slated for
  removal — `TODO.md`).

### API key for mutating endpoints (audit #3)

> Branch `fix/pump-control-safety-module` (2026-06-13). Implements the audit's
> **action-order item #3 — "lock down the API"** (CRIT-Security).
> Sources: `docs/audits/2026-06-11 CodeAudit.md`,
> `docs/handoffs/2026-06-13 - 01 - API key for mutating endpoints (audit 3).md`.

#### Added
- **`api/tethys_api/permissions.py`** — `ApiKeyForWrite`: a single shared API key
  now gates **all mutating requests** (POST/PUT/PATCH/DELETE) via an `X-API-Key`
  header, compared constant-time, fail-closed. Safe methods (GET/HEAD/OPTIONS)
  stay open, so reads and the CORS preflight are unaffected.
- **`globals/secrets.py`** (git-ignored) as the single key source read by both the
  Django API and the core, with a committed `secrets.example.py` template.
- **Web Settings popup** (`layout.html`) — masked field to store the key locally
  (browser `localStorage`); `common.ts` injects the header into the four mutating
  fetch wrappers; `channel.ts` prompts to set the key on a 403.
- **`install/deploy-static.sh`** — one-command frontend deploy (`tsc` + copy to
  the nginx `staticcollect` dir + permissions).
- **`api/tethys_api/tests/test_api_key.py`** — 7 tests covering the permission.

#### Changed
- **`api/tethys_api/settings.py`** — loads `TETHYS_API_KEY`, sets `REST_FRAMEWORK`
  defaults (permission class; empty auth classes to avoid session/CSRF), and adds
  `x-api-key` to `CORS_ALLOW_HEADERS`.
- **`core/apiInterface.py`, `core/radio.py`** — send the key on their POSTs
  (action log, sensor data).
- **`install/install.sh`** — generates `secrets.py` with a random key on first
  install (idempotent) and prints it.

#### Known limitations
- Traffic is plain HTTP on the LAN, so the key is sniffable (raises the bar, not
  transport security). `initializeDatabase` is a state-changing GET and stays open
  under the method-based scope. `DEBUG=False` and moving the Django `SECRET_KEY`s
  into `secrets.py` remain follow-ups (the secrets-file convention is now in place).

### Pump-control safety module — phase 1

> Branch `fix/pump-control-safety-module`, commit `f992d87` (2026-06-13).
> Implements the audit's **action-order item #2 — [C-02] "no pump max-runtime
> kill-switch"** — for the **automatic / core watering path**, plus the
> 6-vs-5 channel `IndexError`, and adds the project's first test suite.
> Sources: `docs/audits/2026-06-11 CodeAudit.md`,
> `docs/handoffs/2026-06-13 - 00 - Pump-control safety module (phase 1).md`.

#### Added
- **`core/gpioAdapter.py`** — GPIO is now reached through a `GpioAdapter` seam so
  the controller never imports `lgpio` directly. `LgpioAdapter` (lazy `lgpio`
  import; per-operation open → claim → write → close) for production;
  `FakeGpioAdapter` records every write for tests; `GpioError` normalises
  backend errors.
- **`core/pumpController.py`** — single deep pump-control module for the core
  path: `run_pump` / `activate` / `deactivate` / `stop_all` / `is_running`. Hard
  **`MAX_PUMP_SECONDS = 300`** flood clamp, `threading.Timer` auto-off,
  `try`/`finally` best-effort drive-LOW on failure, real success/failure returns,
  valve shared-PUMP-pin ref-counting, channel-bounds validation, and a
  `max_concurrent` guard (default `1`). `make_controller()` wires `lgpio` and
  drives all lines LOW on construction (fail-safe boot).
- **First test suite** — `code/master/core/tests/` (16 tests, runnable without
  `lgpio`), `pytest.ini`, and `install/python-requirements-dev.txt` (pytest only,
  dev-only — production requirements untouched). Addresses the audit's
  "zero tests" finding for this module.
- **Fail-safe shutdown** in `core/tethys_core.py` — `pumpController.shutdown()`
  registered on `SIGTERM` and `atexit`, driving all lines LOW so a crash or
  restart can never leave a pump energised.

#### Changed
- **`core/actionEngine.py`** — the watering path now calls `run_pump`
  **non-blocking**; the DB action-log write moved into the timer's `on_complete`
  callback, so the radio keeps listening while a pump runs. A channel deferred
  because the controller is busy keeps its flag set and retries on the next loop
  pass.
- **`core/tethys_core.py`** — builds the pump controller once and passes it to
  `handleActions`; drives all lines LOW on boot.
- **Behaviour change:** pumping is now timer-driven / non-blocking, and
  `max_concurrent = 1` defers a second simultaneous channel to the next loop pass
  (previously concurrent). Reverting to concurrent is a one-line default.
- **`core/hardware.py` / `core/config.py`** — `CHANNEL_COUNT`
  (`= len(Pins.CHANNELS) = 5`) is now the single source of truth;
  `FlagHandler.channelFlags` length derives from it.

#### Fixed
- **[C-02] (automatic path)** — a pump could turn on and never turn off. Every
  "pump on" is now clamped to `MAX_PUMP_SECONDS` and has a guaranteed off (timer
  + `try`/`finally`), closing the worst verified audit risk for the core path.
- **6-vs-5 channel `IndexError`** — `FlagHandler` previously had 6 hardcoded
  flags while only 5 GPIO channel pins exist; `core/radio.py` now ignores packets
  from pipes beyond `CHANNEL_COUNT` instead of indexing past the list.
- **Lying success returns** — the new controller reports the real result of GPIO
  writes (`False` on failure) instead of the old `channel.setOutputState`
  "return `True` even after a swallowed error" behaviour.

#### Deprecated
- **`core/channel.py`** — kept only for the Django API's manual
  activate/deactivate path, now carrying a deprecation note. Scheduled for removal
  in phase 2 when the API is routed through the controller. Do not add new
  callers.

#### Removed
- Dead `FLAG_HANDLER` singleton from `core/config.py`.

#### Known limitations / still open (by design — deferred)
- **[H-01] two GPIO owners** remains open: the core (`pumpController`) and the API
  (`channel.py`) both still claim GPIO per-operation. The per-operation lifecycle
  is kept deliberately so the new module coexists with the API without
  `GPIO_BUSY`. Closing H-01 is **phase 2** (API → core command queue).
- **[C-02] manual-activate auto-off** is implemented for `pumpController.activate()`
  but **not yet wired to the API's `channel_single_action`** — the API manual
  "activate" still has no server-side auto-off until phase 2.
- **[C-01] core async startup** untouched — assessed as mostly a false alarm (the
  synchronous `while True` does run watering + radio; only `fan.control_fan()` is
  never scheduled). The async fix is deferred and is a co-requisite of phase 2.
- Not in this change: API authentication, `DEBUG = False`, `SECRET_KEY` out of
  git, silent-phase timezone/type-filter fixes, `requests` timeouts, the
  polling-timer leak, and firmware findings.
