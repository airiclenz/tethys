<div align="center">
<img src="graphics/logo/tethys%20logo.svg" alt="Tethys logo" width="200">

**A self-hosted, multi-channel automatic plant-watering system.**
</div>

Battery-powered wireless soil-moisture sensors report to a Raspberry Pi master
over a 2.4 GHz nRF24 radio link. The master decides when to water, drives the
pumps/valves, and serves a real-time web dashboard — all on your own LAN, no
cloud.

## Part 1 — What Tethys is and how to use it

### The big picture

Tethys has two kinds of hardware:

1. **Sensor nodes** (one per plant/pot, up to 5) — a battery-powered ATtiny84
   board with a capacitive soil-moisture probe and an nRF24L01+ radio. Each node
   sleeps almost all the time, wakes on a configurable interval, measures soil
   moisture and battery voltage, transmits a reading, and goes back to sleep.
   Designed to run for months on a single charge (~9 µA while sleeping).

2. **The master** — a Raspberry Pi with a custom HAT carrying the matching
   nRF24L01+ radio plus pump/valve driver outputs. The master listens for sensor
   readings, stores them, and when a channel's soil drops below its trigger
   threshold it runs that channel's pump (or opens its valve) for a configured
   duration. It also serves the web UI you use to configure and monitor
   everything.

```
   ┌─────────────┐   nRF24 2.4GHz      ┌──────────────────────────────────┐
   │ Sensor node │  (250kbps, 8-byte   │         Raspberry Pi master      │
   │  ATtiny84   │   versioned frames) │                                  │
   │  + moisture │ ◄──── reading ────► │  core daemon ─► pump/valve GPIO  │
   │  + nRF24    │      config ◄────   │              │                   │
   │  (battery)  │                     │  Django API (SQLite) ◄─► web UI  │
   └─────────────┘                     └──────────────┬───────────────────┘
        × up to 5                                     │  HTTP / WebSocket
                                                      ▼
                                              Your browser / phone
```

Each **channel** (1..5) pairs one sensor node with one pump or valve output.
A channel knows its soil-moisture trigger %, its pump run duration, and how
often its sensor should measure.

### Repository layout

```
tethys/
├── code/
│   ├── master/            # Everything that runs on the Raspberry Pi
│   │   ├── core/          # The watering daemon (radio + pump control + action engine)
│   │   ├── api/           # Django REST API (the system's database + state)
│   │   ├── web/           # Django + Channels dashboard (browser UI)
│   │   ├── watchdog/      # Daily service-restart / log-vacuum job
│   │   ├── globals/       # Shared config + git-ignored secrets
│   │   └── install/       # install.sh, systemd units, nginx configs
│   └── sensor/            # Arduino/PlatformIO firmware for the sensor nodes (the "wpw" project)
├── hardware/              # KiCad schematics + Gerbers for the Pi HAT and the sensor PCB
├── graphics/              # Logos, hardware labels, web-UI assets, renders
└── docs/                  # Audits, protocol review, hardening notes, handoffs
```

### Hardware

**Master — Raspberry Pi + "WaterPlant Pi" HAT** (`hardware/rpi hat/`).
GPIO assignments live in [`code/master/core/hardware.py`](code/master/core/hardware.py):

| Function          | BCM pin(s)            | Notes                                            |
|-------------------|-----------------------|--------------------------------------------------|
| Channel outputs   | `16, 19, 20, 26, 21`  | One per channel; `CHANNEL_COUNT = 5`             |
| Shared pump pin   | `6`                   | Energised together with a channel in **valve** mode |
| Water-level sensor| `4`                   |                                                  |
| nRF24 CE / CSN / IRQ | `22 / 0 / 17`      | SPI radio                                         |
| Status LED / Fan  | `14 / 15`             |                                                  |

A channel of type **pump** drives its own pin directly. A channel of type
**valve** drives its pin *and* the shared `PUMP` pin (one pump pushing water
through whichever valves are open); the pump pin is reference-counted so it
only drops once the last valve closes.

**Sensor node — "Sensor" PCB** (`hardware/sensor/`), firmware in `code/sensor/`:

- **MCU:** ATmega/ATtiny84 @ 8 MHz (PlatformIO `TX` build), deep-sleep
  `SLEEP_MODE_PWR_DOWN`, woken by the 8-second watchdog timer.
- **Radio:** nRF24L01+ on CE=8 / CSN=9, 250 kbps, CRC-8, auto-ACK.
- **Moisture:** capacitive probe excited by a ~500 kHz square wave (Timer0 on
  `PB2`), read on ADC `PA3`; calibration min/max stored in EEPROM.
- **Battery:** monitored on `A7` against the internal 1.1 V reference; below
  **3.2 V** the node sends a battery-alert frame instead of a normal reading.

### Install (on the Raspberry Pi)

```bash
sudo apt install git -y
git clone https://github.com/airiclenz/tethys.git tethys
cd tethys/code/master/install
./install.sh
```

The installer updates the OS, creates a Python venv, installs Redis + nginx,
runs the Django migrations, registers the systemd services, enables SPI, and
**reboots** (re-run `./install.sh --rebooted=true` afterward if you decline the
auto-reboot). On first run it generates a random **API key** into the
git-ignored `code/master/globals/secrets.py` and **prints it** — copy it.

Useful flags:
- `--debug=true` — developer install (also installs the TypeScript toolchain).
- `--allowed-hosts=tethys.<tailnet>.ts.net` — extra `ALLOWED_HOSTS` for remote
  (VPN) access. Alternatively (and preferred per-install), list the name in the
  git-ignored `code/master/globals/allowed_hosts.py` (copy `allowed_hosts.example.py`)
  — no reinstall needed, just restart the services. See
  [`docs/remote-access-hardening.md`](docs/remote-access-hardening.md).

After it's up: open `http://<pi-host>/` in a browser → **Settings** (top menu) →
paste the API key → Save. The key gates **every** request (reads included; only
the CORS `OPTIONS` preflight is exempt), so the dashboard stays blank until it's
set. If a page can't authenticate (missing or wrong key), a warning banner
appears under the header with a link straight to Settings.

### Daily use

- **Sensor Readings page** (`/`) — per-channel reading history: two trend charts
  (moisture % and battery voltage over time) sit above a sortable table of the
  individual readings.
- **Channels page** (`/channels/`) — live moisture %, battery, last action per
  channel; enable a channel, set its nickname, type (pump/valve), pump duration,
  and the moisture trigger %; manually test a pump.
- **Schedules page** (`/schedules/`) — define **silent phases** (quiet hours):
  weekday + start time + duration windows during which *all* automatic watering
  is suppressed (e.g. overnight). The header shows a sleep icon while a silent
  phase is active.
- **Order 66** (top menu) — recovery action for when a service or the Pi itself
  gets wedged: confirm the popup and the Pi performs a graceful reboot (back in
  ~1 minute). Gated by the API key, like pump control.
- The dashboard updates live over a WebSocket; no manual refresh needed.

### Updating / operating

From `code/master/install/`:
- `./installServices.sh` — re-deploy the systemd services from the current code.
- `./services-restart.sh`, `./services-stop.sh`, `./services-clearLogs.sh`.
- `./deploy-static.sh` — rebuild the frontend TypeScript and publish it to nginx.

The five services: `tethys-core`, `tethys-api`, `tethys-web`, `daphne`, and
`tethys-watchdog` (the last restarts core+api nightly at 01:00 and vacuums the
journal).

### Firmware (sensor nodes)

Built with [PlatformIO](https://platformio.org/) from `code/sensor/`. Before
building, set the node identity in [`code/sensor/include/wpw_Config.h`](code/sensor/include/wpw_Config.h):
`SENSOR_NUMBER` (1–5). Flash with:

```bash
cd code/sensor
pio run -t program -e tethys-sensor     # via an AVR ISP programmer
```

> ⚠️ **The master and every sensor must be flashed together.** The wire format
> is versioned and fixed-size; a node on mismatched firmware fails the version
> check and goes silent (cleanly — it never corrupts data). See the
> *Known limitations / coordinated flash* note in [`CHANGELOG.md`](CHANGELOG.md).

### Sensor node LED — calibration & status blinks

A sensor node has no screen; its single onboard LED is how it talks to you.
Patterns are produced by `DoSimpleBlink(onMs, offMs)` and `DoSoftPulse(ms)`
([`code/sensor/src/wpw_Blinker.cpp`](code/sensor/src/wpw_Blinker.cpp); the soft
pulse is a software-PWM glow, since the LED pin has no free hardware PWM).

**How calibration works.** Calibration maps the probe's raw reading onto a
0–100 % moisture scale, and it is **two-point**: the node captures one reading in
a *wet* condition and one in a *dry* condition, then stores the lower value as
`MinimumValue` (wettest) and the higher as `MaximumValue` (driest) in EEPROM
(`Calibrate()` in [`code/sensor/src/wpw_Sensor.cpp`](code/sensor/src/wpw_Sensor.cpp)).
Later readings become `100 − map(raw, min, max, 0, 100)` %.

1. Trigger it from the web UI — set the channel's **calibrate** flag
   (`sensorTriggerCalibration`), then **power-cycle or reset the node**.
   Calibration runs only as part of the **boot-time** config exchange (the full
   `GETCONFIG` in `setup()`) — *not* on a normal measurement wake. A running node
   re-pulls its config periodically (see *Periodic config pull* below), but those
   pulls are deliberately **settings-only**: they carry measure-frequency /
   TX-power but never the calibration trigger, so they can't run calibration
   mid-life. The master delivers the trigger once and immediately clears the flag
   (`core/radio.py`), so if you set the flag while the node is already running,
   nothing happens until you reset it. (This is the usual reason a calibration
   "didn't start".)
2. The node then takes **two** measurements, each announced by the *calibration
   countdown* below (slow blinks → fast blinks → one long blink → it measures
   while the LED is off). Put the probe in one condition for the first capture
   and the other condition for the second.
3. **Order doesn't matter** — the firmware sorts the two readings into min/max.
   What matters is that the two conditions are genuinely different: if the two
   readings are too close, the calibration is **rejected** and the previous
   values are kept (signalled by the long 2 s blink).

**First reading after boot.** On every boot — including right after calibration —
the node waits ~1 minute (`STARTUP_SETTLE_SECONDS`, default 60, in
[`wpw_Config.h`](code/sensor/include/wpw_Config.h)) before taking and transmitting
its first reading. It *sleeps* through the wait (you'll see the heartbeat flash
each ~9 s), so it costs almost no power. Put the probe in its final monitoring
position before this window ends — the first reported value reflects wherever the
probe is at that moment, **not** the calibration captures.

**Periodic config pull.** A running node re-pulls its config so web-UI changes
(measure frequency, transmission power) reach it without a power-cycle. The cadence
is `PULL_CONFIG_CYCLE_SECONDS` in [`wpw_Config.h`](code/sensor/include/wpw_Config.h)
(default `3600` = 1 h; **`0` disables it** for maximum battery saving). To stay
gentle on the battery the pull **rides an existing measurement wake** — the radio
is already powered up, so it adds no extra power-up, and the master answers from
its warm `ConfigCache` so the listen window is usually a few milliseconds. The pull
therefore happens on the first measurement at/after the cycle has elapsed since the
last pull. These pulls are **silent** (no LED) and **settings-only** — they never
carry or clear the calibration trigger (calibration stays boot-only; see above).

The patterns, all on the sensor (TX) node LED:

| Event | Blink pattern | Meaning |
|-------|---------------|---------|
| **Power-on / node ID** | `N` slow blinks (150 ms on, 300 ms off), where `N` = `SENSOR_NUMBER` | Node booted and is powered; the count identifies which node it is (1–5). |
| **Config received** | a soft ~2 s glow (brightness ramps up then down) | The master answered the config request (at boot) and the settings were applied. |
| **No master reply** | two short flashes (15 ms) | Config request timed out (no answer within 500 ms); the node falls back to the settings stored in EEPROM. |
| **Config rejected** | three short flashes (15 ms) | The master replied but the frame failed the protocol-version / type check. |
| **Settings saved** | accelerating ramp — 150 → 100 → 75 → 50 → 25 → 15 ms — then one long 300 ms flash (ramps *up* to a strong finish) | New settings differed from EEPROM and were written. |
| **Settings unchanged** | decelerating ramp — 15 → 25 → 50 → 75 → 100 → 150 ms — fading out with no final flash (the mirror of *saved*) | Config was checked but nothing changed, so nothing was written. |
| **Heartbeat** | one very short flash (5 ms) each wake (~every 9 s) | Normal sleep/measure loop tick — the node is alive. |
| **Transmit failed** | four short flashes (15 ms) | The radio send failed; the node backs off (~15 min) before retrying. Part of the short-flash radio-error family, counted: 2 = no reply, 3 = bad frame, 4 = send failed (a *successful* config exchange is the soft glow above instead). |
| **Calibration countdown** | 10 slow blinks (300 ms) → 20 fast blinks (100 ms) → one long blink (1 s) → LED off while it measures | Counts down to a calibration capture. Runs **twice**, once per measurement point. |
| **Calibration rejected** | one very long flash (2 s) | The two calibration readings were too close together; calibration was discarded and the previous values kept. |

---

## Part 2 — Orientation for a contributor or coding agent

This half is the lightweight `CLAUDE.md`: the runtime topology, the invariants
that are easy to break, and where to look. Read it before changing anything on
the master.

### Process & port map

Everything runs on the Pi as systemd services (units in
`code/master/install/assets/*.service`, nginx in `*.nginx`):

| Service           | Process                         | Binds        | Reached via            |
|-------------------|---------------------------------|--------------|------------------------|
| `tethys-core`     | `core/tethys_core.py` (asyncio) | — (GPIO/radio) | n/a                  |
| `tethys-api`      | gunicorn → `tethys_api.wsgi`    | `localhost:5001` | nginx **:5000**    |
| `tethys-web`      | gunicorn → `tethys_web.wsgi`    | `localhost:8000` | nginx **:80** `/`   |
| `daphne`          | ASGI → `tethys_web.asgi`        | `0.0.0.0:8001`   | nginx **:80** `/ws/`|
| `tethys-watchdog` | `watchdog/tethys_watchdog.py`   | —            | nightly restart        |
| redis-server      | Channels layer for daphne       | `localhost:6379` | —                  |

**The API is the single source of truth.** Both the core daemon and the web
backend treat it as the database boundary and reach it at `http://localhost:5000/api/`
(nginx → gunicorn:5001). It is Django REST Framework over **SQLite**
(`api/db.sqlite3`).

### Data flow (one reading → one watering)

1. A sensor wakes, measures, and transmits a 7-byte frame on its pipe.
2. `core/radio.py` (`checkRadioInbox` → `handlePayload`) drains the RX FIFO,
   validates each frame via `core/protocol.py`, and `POST`s the reading to
   `sensorData/`. On success it sets that channel's flag in
   `core/config.py::FlagHandler.channelFlags`.
3. `core/actionEngine.py::handleActions` (called each core-loop pass) checks the
   **silent phase** first (fail-closed — see below), then for each flagged
   channel pulls `channelSummary/<n>` and, if `moisture <= trigger` and the
   channel is enabled, calls `pumpController.run_pump(...)`.
4. `core/pumpController.py` energises the line, arms a `threading.Timer`
   auto-off, and on completion writes an `actionLog/` entry — all non-blocking,
   so the radio keeps listening while a pump runs.
5. The web UI sees the change: `web/tethys_web/jobs.py` polls the API every 10 s
   (`/lastUpdate/`, `/channelSummary/`, `/schedule/`, `/silentPhaseStatus/`) and,
   on a change, broadcasts to all browsers over the `/ws/tethys/` WebSocket
   (`web/tethys_web/consumers.py`).

A **manual *Test Channel* tap** uses the same hardware path, not a separate one:
the API enqueues a `ManualCommand` (it never drives GPIO), the core drains it each
loop pass and runs it through the same `pumpController` (rejecting an activate when
another channel is already running), and writes the outcome back for the UI to
poll. This is what keeps the one-channel power limit holding for manual control —
see *Invariants* below.

When a sensor asks for its config (`GETCONFIG`), the master answers from an
in-memory `ConfigCache` (warmed out-of-band by `Radio.refreshConfigCache`), never
with a blocking HTTP call inside the sensor's short listen window. A running node's
periodic, settings-only pull (`GETCONFIG_PERIODIC`) is answered the same way but
with the calibration trigger stripped and never cleared.

### Invariants — break these and something physical or silent goes wrong

- **Pump safety.** Every "pump on" is clamped to `MAX_PUMP_SECONDS = 300` and has
  a guaranteed off (timer + `try/finally`). The controller drives all lines LOW
  on construction (fail-safe boot) and on `SIGTERM`/`atexit`. Never reintroduce a
  watering path that bypasses `pumpController`. `make_controller()` is the *only*
  place `lgpio` is bound; all hardware goes through the `GpioAdapter` seam so the
  logic is testable without a Pi.
- **One channel at a time (power limit).** `pumpController` is the *single owner*
  of the watering GPIO. Both automatic watering and the web UI's manual *Test
  Channel* taps go through it — the latter via the `ManualCommand` queue the core
  drains each loop pass — so its `max_concurrent = 1` guard holds the invariant
  that **at most one channel (plus the shared pump pin) is ever energised**, which
  protects the power supply. A manual activate that arrives while another channel
  is running is *rejected*, not run. The API process never drives GPIO itself.
- **Silent phase is fail-closed.** If the API is unreachable, `isInSilentPhase()`
  returns `None` and `actionEngine` **skips watering** for that pass — it must
  never water on unknown state. The window math lives in
  `api/tethys_api/silentphase.py` (stdlib-only, unit-tested independently of
  Django).
- **Timezones.** `globals/config.py::TIME_ZONE` (`Europe/Stockholm`) is the
  single deployment/display zone, shared by `core` and `web`. The **Django API
  deliberately keeps `TIME_ZONE = 'UTC'` as its storage zone** — schedule start
  times are wall-clock times-of-day stored on a placeholder date; the deployment
  zone is applied only at silent-phase evaluation. Don't "fix" the API to local
  time. (See the silent-phase fixes in `CHANGELOG.md` for why.)
- **Wire protocol is versioned and fixed-size.** `core/protocol.py` and
  `sensor/include/wpw_RXTX.h` / `wpw_Config.h` must stay byte-for-byte in sync:
  `PROTOCOL_VERSION = 1`, `PAYLOAD_SIZE = 8`, structs `<BBBf>` (sensor→master, 7 B)
  and `<BBHB?>` (master→sensor, 6 B). Bump `PROTOCOL_VERSION` on *any* layout
  change — and re-flash everything (no backward compat). Adding a new *message
  type* (the type byte, e.g. `DATATYPE_CMD_GETCONFIG_PERIODIC = 8`) is **not** a
  layout change, so it does not bump the version; keep the type constants in sync
  on both ends. An un-updated peer ignores an unknown type (the sensor's periodic
  pull just times out and retries), so mixed versions degrade gracefully.
- **Pipe 0 is reserved.** Channels map 1:1 onto nRF24 reading pipes 1..N; pipe 0
  is the ACK/writing address. This caps the link at 5 sensors. See
  `protocol.pipe_for_channel`.
- **`CHANNEL_COUNT` is the single source of truth** (`= len(Pins.CHANNELS) = 5`).
  The DB/radio reference 6 channels historically; a 6th needs a physical GPIO pin
  first. Don't hardcode channel counts.
- **Secrets.** `globals/secrets.py` (git-ignored) holds `TETHYS_API_KEY`,
  `API_SECRET_KEY`, `WEB_SECRET_KEY`, and is read by *both* the Django apps and
  the non-Django core. Template: `globals/secrets.example.py`. Every API request
  needs `X-API-Key` (reads included; only CORS `OPTIONS` is exempt) — see
  `api/tethys_api/permissions.py::ApiKeyRequired`.

### Auth posture

A single shared API key gates **all** requests, compared constant-time,
fail-closed. The core (`apiInterface.py`, `radio.py`) and the web backend
(`jobs.py`, `tools.py`) send it server-side; the browser stores it in
`localStorage` and `common.ts` injects it into every fetch. Transport is plain
HTTP on the LAN — for remote access, front it with a VPN overlay (Tailscale/
WireGuard), not an open port. See [`docs/remote-access-hardening.md`](docs/remote-access-hardening.md).

### Data model (Django, `api/tethys_api/models.py`)

- **Channel** (`number` PK) — `enabled`, `nickName`, `channelType` (pump/valve),
  `actionTriggerPercent`, `pumpDurationSeconds`, `sensorMeasureFrequencyMinutes`,
  `sensorTriggerCalibration`, `sensorTransmissionPowerLevel`.
- **SensorData** — `channel` FK, `moisturePercent`, `batteryVoltage`, `timestamp`.
- **ActionLog** — `channel` FK, `actionType`, `startTime`, `endTime`.
- **Schedule** — `weekday`, `scheduleType` (`silent`), `startTime` (UTC wall-clock),
  `durationMinutes`, `enabled`.
- **ManualCommand** — `channel` FK, `action` (activate/deactivate), `status`,
  `message`, `requestedAt`, `processedAt`. The web UI enqueues a manual *Test
  Channel* tap here; the core drains it through `pumpController` (the API never
  drives GPIO) and reports the outcome back for the UI to poll.
- Lookup tables: `ChannelType`, `ActionType`, `ScheduleType`, `TransmissionPowerLevel`.
- `channelSummary/<n>` is the denormalized read both the core and UI consume
  (channel config + latest sensor reading + counts).

### Tests

**Backend (core + API)** — pure Python, no Pi/hardware needed:

```bash
cd code/master
pip install -r install/python-requirements-dev.txt   # pytest, dev-only
pytest                                                # pytest.ini sets paths
```

Covers the parts that gate physical action or silent failure: `core/tests/`
(pump controller, GPIO adapter, protocol framing, action engine, manual-command
queue) and `api/tethys_api/tests/` (API-key permission, silent-phase window math,
`LAST_DATA_UPDATE` wiring, manual-command lifecycle). All run without `lgpio`/`pyrf24`/a Pi, thanks to the
GPIO and protocol seams. **Add tests behind those seams when you touch the
watering, radio-framing, or silent-phase paths.**

**Web UI (Playwright)** — browser-driven regression tests for the channels UI:

```bash
cd code/master/web
pip install -r requirements-dev.txt
playwright install --with-deps chromium   # downloads Chromium + apt libs (needs sudo)
pytest
```

These drive a headless Chromium against a throwaway Django live server, exercising
the real compiled JavaScript (`conftest.py` compiles `static/ts` → `static/js`
first), so they catch DOM/click-handler bugs the Python suites can't. See
[`web/tests/README.md`](code/master/web/tests/README.md) for what's covered and how
it works. A developer install (`install.sh --debug=true`) installs all of the above
automatically.

### Frontend build

TypeScript sources in `web/static/ts/` compile to `web/static/js/` via
`compile.sh` (`tsc`) / `compileAutomatically.sh` (watch). The build is strict
(`strict: true` in `tsconfig.json`) and `tsc -p tsconfig.json` compiles cleanly.
Use `install/deploy-static.sh` to compile + publish to the nginx static dir. The
compiled `web/static/js/` is git-ignored — it is rebuilt from the `.ts` sources on
deploy and before the UI tests, so the TypeScript is the single source of truth.

> ⚠️ **Editing the frontend? Change the `.ts` files in `web/static/ts/`, never
> `web/static/js/` directly.** The `.js` folder is generated output (git-ignored)
> and is overwritten on every `tsc` run / deploy, so any hand-edits to the `.js`
> are silently lost. Tip: `git check-ignore <path>` will tell you if a file is a
> build artifact before you touch it.

### Known limitations / deferred (see `CHANGELOG.md` + `docs/`)

- Low-battery flag is logged but not persisted (no `SensorData` column yet).

### Where the design rationale lives

`docs/audits/` (code audit, architecture review, protocol review) and
`docs/handoffs/` capture *why* the current shape exists — the pump-safety module,
the API-key lockdown, the protocol hardening, and the silent-phase timezone fixes.
`CHANGELOG.md` is the readable summary of each. Start there before reworking any
of the invariants above.
