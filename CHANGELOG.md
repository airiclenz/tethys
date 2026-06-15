# Changelog

All notable changes to Tethys are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Current released version: **2.0.0** (`code/master/globals/config.py`).

---

## [Unreleased]

### Sensor Readings: moisture & battery-voltage trend charts

> (2026-06-15). The Sensor Readings page only listed raw readings in a table, so
> trends over time were hard to see at a glance. It now shows two time-series line
> charts — moisture % and battery voltage — side by side above the table, drawn
> entirely from data the page already loads.

#### Added
- `code/master/web/static/ts/charts.ts` (`tethys.charts`) — renders the moisture
  and battery-voltage line charts for the selected channel from the readings
  `measurements.ts` already fetches. Charts update in place on channel change /
  delete and clear when a channel has no data.
- `code/master/web/static/vendor/chart.umd.min.js` — Chart.js v4.4.6 (UMD),
  self-hosted so the dashboard keeps working offline (no CDN). `installServices.sh`
  and `deploy-static.sh` now publish the `vendor/` folder to `staticcollect`, and
  `layout.html` loads it before the app scripts.

#### Changed
- **`web/templates/index-measurements.html`** — two chart cards (moisture /
  battery voltage) added above the readings table.
- **`web/static/ts/measurements.ts`** — `render()` now also refreshes the charts.
- **`web/static/css/main.css`** — chart card / canvas styling.

### Remote access: nginx catch-all + git-ignored extra `ALLOWED_HOSTS`

> (2026-06-15). Reaching the Pi by a name other than `tethys.local` (e.g. its
> Tailscale name) used to fall through to the stock "Welcome to nginx!" default
> site, and required baking the hostname into the systemd units at install time.
> The web vhost is now the catch-all `default_server` and the host allow-list can
> be set per-install in a git-ignored file with only a service restart.

#### Added
- `code/master/globals/allowed_hosts.py` (git-ignored, with committed
  `allowed_hosts.example.py`) defining `EXTRA_ALLOWED_HOSTS`. Both Django settings
  read it at runtime and append it to `ALLOWED_HOSTS`; the import is non-fatal, so
  an absent file just means no extra hosts. The existing `--allowed-hosts` flag /
  `TETHYS_ALLOWED_HOSTS` env var still work and are unioned in.

#### Changed
- **`install/assets/tethys-web.nginx`** — the web site is now
  `listen 80 default_server` on IPv4 **and** `[::]:80` (dual-stack), so it serves
  Tethys for any Host header / IP.
- **`install/installServices.sh`** — removes the stock nginx default site
  (`/etc/nginx/sites-enabled/default`) so it can't own `default_server` or shadow
  the app.
- Docs (`docs/remote-access-hardening.md`, `README.md`) updated for the file-based
  host list and the catch-all vhost; fixed the remote-access URL to port 80 (the
  `:8000` gunicorn port is loopback-only).

### Remove the legacy Arduino `#ifdef RX` receiver firmware

> (2026-06-14). The firmware in `code/sensor/` used to compile into two roles
> selected by a `#define TX` / `#define RX` switch: the battery sensor node (TX)
> and a standalone Arduino Leonardo receiver/master (RX) with an OLED, buttons,
> and pump/valve outputs. The RX master was superseded by the Raspberry Pi master
> (`code/master/`) and was no longer built or flashed, so its half of every shared
> file was dead weight. The project now builds a **single firmware** — the sensor
> node — with no role macro at all. No behaviour change to the sensor, and the
> wire protocol is untouched (`PROTOCOL_VERSION` stays **1**).

#### Removed
- RX-only modules `wpw_UI`, `wpw_Input`, `wpw_Pumps` (`.cpp` + `.h`), the
  `platformio.ini.RX` build env, and the orphaned `pre-build.py` (it was wired in
  only via the RX build's `extra_scripts`).
- Every `#ifdef RX` block across the shared files (`wpw_RXTX`, `wpw_Sensor`,
  `wpw_Blinker`, `wpw_EEPROM`, `wpw_Config`, `WirelessPlantWatering.cpp`).

#### Changed
- The now-always-true `#ifdef TX` guards and the `#define TX` / `#define RX`
  selector in `wpw_Config.h` are gone; the TX paths are unconditional. The sole
  PlatformIO env is renamed `[env:TX]` → `[env:tethys-sensor]` (now that there is
  only one role): `pio run -e tethys-sensor`.

### Periodic config pull — push config changes to running nodes without a reboot

> (2026-06-14). Previously a sensor only fetched its config at boot
> (`RequestConfiguration()` in `setup()`), so a measure-frequency or TX-power
> change made in the web UI didn't reach a running node until it was manually
> power-cycled. Nodes now re-pull their config on a configurable cycle. The pull
> **rides an existing measurement wake** (the radio is already powered up), so it
> adds no extra radio power-up; the master answers from its warm `ConfigCache`,
> so the listen window is usually a few milliseconds. Set
> `PULL_CONFIG_CYCLE_SECONDS = 0` to disable periodic pulls entirely (the feature
> compiles out — zero cost — for maximum battery saving); the boot-time fetch
> still happens. The existing `GETCONFIG`/`CONFIG` handshake is reused; the wire
> layout is unchanged, so `PROTOCOL_VERSION` stays **1**.
>
> Calibration stays a **boot-only**, user-supervised operation. The periodic pull
> uses a distinct settings-only request (`DATATYPE_CMD_GETCONFIG_PERIODIC = 8`)
> that the master answers with measure-frequency / TX-power only, never carrying
> or clearing the one-shot calibration trigger — so an hourly pull can't silently
> consume a pending calibration request.

#### Added
- **`sensor/include/wpw_Config.h`** — `PULL_CONFIG_CYCLE_SECONDS` (default `3600`,
  `0` = disabled), the re-pull cadence in seconds.
- **`sensor/include/wpw_RXTX.h` + `core/protocol.py`** — new message type
  `DATATYPE_CMD_GETCONFIG_PERIODIC = 8` (sensor → master), kept in sync on both ends.
- **`core/tests/test_radio_sendconfig.py`** — periodic-pull never clears the
  calibration flag and strips the trigger while preserving the real settings.

#### Changed
- **`sensor/src/WirelessPlantWatering.cpp`** — `loop()` re-pulls config on the
  first measurement at/after `PULL_CONFIG_CYCLE_SECONDS` has elapsed (guarded by
  `#if`, so disabling costs nothing); persists changed settings silently.
- **`sensor/src/wpw_RXTX.cpp`** — `RequestConfiguration(bool periodic = false)`:
  the periodic path uses the new opcode, never triggers calibration, and stays
  silent (no LED) to save awake time.
- **`sensor/wpw_EEPROM.{h,cpp}`** — `SaveSettingsToEeprom(bool showFeedback = true)`
  for a silent save from the running loop.
- **`core/radio.py`** — `handlePayload` routes the periodic opcode to
  `sendConfig(channelNo, includeCalibration=False)`, which sends settings only and
  never clears the calibration flag.

### TypeScript strict-mode cleanup (clean `tsc` build)

> (2026-06-14). The frontend `web/static/ts/` sources (one `namespace tethys`)
> compiled with **311 pre-existing type errors** (implicit-any, possibly-null)
> under a `tsc` that defaults `strict` on — surfaced as "compile errors" when
> running `install/deploy-static.sh`. Annotated the types and added null/DOM
> assertions so the build is clean, then enabled `strict` explicitly. The fixes
> are **type-level only** (annotations / `!` / casts): the emitted JavaScript is
> unchanged apart from erased-annotation cosmetics and `tool.ts`'s
> namespace-local `this.pad`/`this.getTimeString` becoming direct calls to the
> same functions. No runtime behavior changed.

#### Changed
- **`web/static/ts/tsconfig.json`** — added `"strict": true` and
  `"forceConsistentCasingInFileNames": true`. `tsc -p tsconfig.json` now reports
  **0 errors** (was 311) and `deploy-static.sh` compiles cleanly.
- **`web/static/ts/*.ts`** (`actions`, `channel`, `common`, `measurements`,
  `schedule`, `templatter`, `tool`, `websocket`) — explicit parameter/variable
  type annotations, non-null assertions on `document.getElementById(...)` and
  `response.body`, selection-state/index vars typed to avoid null-index cascades,
  `Templatter` field definite-assignment (`!`), and `authHeaders()` typed
  `Record<string, string>`.

### Preserve sensor calibration across re-flashes (EESAVE) + invalidate stale calibration

> Branch `sensor-eeprom-calib-persist` (2026-06-14). A calibrated node was
> reading 0% in a plant pot. Investigation confirmed the measurement direction
> assumption is **correct** (verified against `hardware/sensor/Sensor.sch`: the
> soil cap `C8` shunts the 500 kHz excitation through `R5` into a `D4`/`C7`/`R6`
> envelope detector, so wetter soil → lower raw reading — matching the firmware's
> `min=wet`/`max=dry` sort and `100 - map(...)` inversion). The 0% was stale,
> wrong-scale calibration: commit `21ec50c` changed the raw ADC scale, but the
> `EESAVE` fuse was off so every flash wiped EEPROM to placeholder defaults
> (650/850) that no longer match the new scale. No measurement/calibration
> *logic* was changed.

#### Changed
- **`sensor/platformio.ini`** — `board_fuses.hfuse` `0xDF` → `0xD7` (clears bit 3
  → `EESAVE` programmed) so the pre-flash chip-erase **preserves EEPROM**.
  Calibration now survives same-version re-flashes; the `VERSION`/`SUBVERSION`
  guard in `InitializeEeprom()` (`sensor/src/wpw_EEPROM.cpp`) becomes the sole
  arbiter of when calibration is re-defaulted. Re-apply with
  `pio run -t fuses -e TX`.
- **`sensor/include/wpw_Version.h`** — `SUBVERSION` `0` → `1`. One-time bump that
  forces `InitializeEeprom()` to discard the stale pre-`21ec50c` calibration and
  rewrite valid defaults on the next boot. **A one-time recalibration of each
  node is required after flashing** (air then water).

#### Notes
- Order on hardware: build (`pio run -e TX`) → apply fuses (`pio run -t fuses -e
  TX`) → flash (`pio run -t program -e TX`) → recalibrate. The master
  calibrate-delivery fix (`4d0877f`) must be deployed for the calibrate trigger
  to reach the node.

### Remove the retired 6th sensor channel

> Branch `remove-6th-sensor` (2026-06-14). Removes the leftover references to a
> 6th sensor/channel. The nRF24L01 has 6 pipes but pipe 0 is reserved for the
> writing/ACK address, so the link tops out at **5** sensor channels (also bounded
> by the 5 pump GPIOs the master exposes). The 6th channel never worked — the RX
> firmware opened reading pipe 5 twice instead of a (non-existent) pipe 6.

#### Removed
- **`sensor/include/wpw_Config.h`, `sensor/src/wpw_RXTX.cpp`** — the
  `PIPE_ADDRESS_6` define and its entry in the firmware `pipes[]` table.
- **`core/radio.py`** — the unused 6th entry (`0x5232443236`) from
  `_pipeAddresses`; the reading-pipe loop already only used pipes 1..`CHANNEL_COUNT`.

#### Changed
- **`api/tethys_api/models.py`** — `initializeDatabase` now seeds `CHANNEL_COUNT`
  (= 5) channels instead of a hardcoded 6, via a new module-level `CHANNEL_COUNT`
  constant (mirrors `core.hardware.CHANNEL_COUNT`).
- **`sensor/include/wpw_Config.h`** — `SENSOR_NUMBER` valid range corrected from
  `1-6` to `1-5` (and the value reset from the now-invalid `6` to `1`; it is a
  per-flash node identity — set it to the node being flashed).
- **`README.md`** — `SENSOR_NUMBER` documented as `1–5` (was `1–6`).

#### Fixed
- **6th-sensor reading-pipe bug** — `SetupRadioForRx()` called
  `openReadingPipe(5, pipes[6])` after `openReadingPipe(5, pipes[5])`, opening
  pipe 5 twice and referencing a 7th address that the 6-pipe radio cannot use.
  The duplicate/out-of-range call is removed; the receiver opens reading pipes
  1..5 cleanly.
- **Stray 6th channel in already-initialized databases** — `initializeDatabase`
  now deletes any `Channel` with `number > CHANNEL_COUNT`, so systems seeded
  before this change drop the orphaned channel 6 from the web UI.

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
- The legacy Arduino `#ifdef RX` firmware receiver has since been **removed**
  (see the entry at the top of this changelog).

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
