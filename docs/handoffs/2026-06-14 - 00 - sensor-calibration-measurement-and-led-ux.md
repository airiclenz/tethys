# Handoff — Sensor calibration & measurement fixes + LED UX

**Date:** 2026-06-14
**Branch:** `fix/sensor-calibration-measurement` (off `main` @ `a515080`)
**Area:** `code/sensor/` (ATtiny84 firmware) + `code/master/core/` (Pi master) + `README.md`

## What this branch does (don't re-derive — read the commits)

Five commits, each self-describing; read `git log` bodies rather than re-reading diffs:

| Commit | Summary |
|--------|---------|
| `21ec50c` | Measurement fix: deterministic excitation timing, averaging, VCC normalization, calibration validity guard, map() div-by-zero guard |
| `d60599a` | README: sensor LED blink-pattern table + calibration explanation |
| `07038e8` | LED UX: transmit-failed → 4 flashes; settings-unchanged → decelerating ramp |
| `9cf696a` | `DoSoftPulse()` software-PWM glow for "config received"; README clarifies calibration is boot-only |
| `4d0877f` | **Master bug fix**: clear the one-shot calibrate flag only on ACKed delivery (+ `core/tests/test_radio_sendconfig.py`) |

The original measurement review (the first deliverable) lives in the plan file
`/home/airic/.claude/plans/tingly-herding-donut.md` — it was overwritten in the last turn with the
calibration-delivery-fix plan, so the earlier full review now exists only as commit `21ec50c`'s
rationale + the README. The findings labels (F1–F8) referenced in chat map to that commit.

## Problem history (why these changes exist)

User reported, in order: (1) measurements jumpy + **narrow range that clips** + **drift over time**;
(2) wanted the LED blink patterns documented; (3) wanted LED UX improvements; (4) wanted
"config received" to be a soft glow; (5) **calibration didn't run even after rebooting the node with
the flag set**.

Root causes found:
- **Range/drift:** `ReadSensor()` excited the probe with `delay(200)` while Timer0 was repurposed as
  the 500 kHz clock (so it was really ~50 ms vs a ~510 ms RC settling τ) → tiny swing, and timing was
  set by the drifting internal RC oscillator. Fixed with a cycle-based `_delay_ms` busy-wait, longer
  window, read-while-excited, averaging, and VCC normalization.
- **Calibration never triggered:** by design a node only requests config at boot (`setup()` →
  `RequestConfiguration`), and the master delivers the calibrate flag once then clears it. The master
  (`core/radio.py::sendConfig`) ignored `radio.write()`'s ACK result and cleared the flag even on an
  **unacknowledged** send (node's ~500 ms listen window had closed) → flag consumed, calibration never
  ran. Fixed in `4d0877f`.

## Current state / uncommitted work

- **Uncommitted edit (NOT mine):** `code/sensor/src/wpw_RXTX.cpp` has a working-tree change adding
  `delay(400);` after `DoSoftPulse(2000);` in `RequestConfiguration()` (plus a trailing-whitespace
  line). Looks like a user tweak (a pause after the config-received glow). **Decide whether to keep +
  commit it.** It does not yet build-verified in CI here.
- Firmware builds clean for `env:TX`. Master suite: **35 passed**.

## Open items for the next session

1. **Resolve the uncommitted `delay(400)`** in `wpw_RXTX.cpp` (commit or revert).
2. **Hardware verification (cannot be done here):**
   - **Recalibrate every node after flashing** — `21ec50c` changes the raw scale, so old EEPROM
     calibration is invalid.
   - Verify the calibrate trigger now works: set flag in UI → reboot node → expect the calibration
     countdown blink (10 slow → 20 fast → 1 long, ×2). Cross-check `tethys-core` journal for
     "Config was sent." vs "Config send was NOT acknowledged".
   - Confirm the node under test was **not** flashed as `SENSOR_NUMBER 6` (`wpw_Config.h:23`, committed
     default) — the master only serves channels 1–5, so a #6 node is invisible.
3. **Deploy the master fix** (`4d0877f` is master-only): restart `tethys-core` on the Pi
   (`code/master/install/services-restart.sh`). No re-flash needed for the calibration trigger.
4. **Tuning:** `SENSOR_EXCITATION_MS = 750` (in `wpw_Sensor.cpp`) is a reasoned default — sweep on
   hardware (scope `PA3`) for best dry/wet spread.
5. **Suggestions offered but not implemented** (user hasn't chosen): low-battery local blink (distinct
   heartbeat when `!IsBatteryOk()`); bump short-flash on-time 15→~35 ms for daylight visibility;
   distinguish calibration point 1 vs 2; quiet gap between back-to-back patterns.
6. **Deferred/latent:** EEPROM version bump to auto-invalidate stale calibration; legacy RX
   `SetupRadioForTx`/`openReadingPipe(5, pipes[6])` duplicate-pipe bug (deprecated Arduino receiver);
   flash usage is now **84.2%** (6894/8192) — watch headroom.

## How to build / test

- Firmware: `cd code/sensor && ~/.platformio/penv/bin/pio run -e TX`
- Master tests: `cd code/master && env_tethys/bin/python -m pytest -q`

## Suggested skills

- **code-review** — audit the branch diff (firmware + master) before merging; touches a physical/
  safety-adjacent path (radio config handshake) and battery-powered timing.
- **pr-lifecycle** — open the PR for `fix/sensor-calibration-measurement` into `main` once the
  uncommitted edit is resolved.
- **verify** — for the on-hardware checks in "Open items" (calibration trigger, recalibration,
  drift/range), if/when a node + Pi are available.
