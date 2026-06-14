# Tethys Communication-Protocol Review — 2026-06-13

> Focused review of the nRF24L01+ link between the battery sensor nodes and the
> Raspberry Pi master, with the fixes applied on branch
> `fix/pump-control-safety-module`. Companion to the broader
> `2026-06-11 CodeAudit.md`.

**Scope:** the wire protocol only — sensor firmware (`code/sensor/src/wpw_RXTX.cpp`,
`code/sensor/include/wpw_RXTX.h`, `wpw_Config.h`, `WirelessPlantWatering.cpp`)
and the master radio driver (`code/master/core/radio.py`). The legacy Arduino
`#ifdef RX` receiver in the firmware is **out of scope** (superseded by the Pi
master; removal tracked in `TODO.md`).

**Prompt:** the owner reported the link "feels unreliable" and asked specifically
for the communication protocol to be made more robust.

**Transport (unchanged):** nRF24L01+, 2.4 GHz, 250 kbps, 5-byte addresses,
hardware CRC-8, hardware auto-ACK. Star topology, master polls/serves up to
`CHANNEL_COUNT` sensors. Sensors deep-sleep between readings.

---

## Executive summary

The unreliability is not RF flakiness — it is a handful of concrete software
defects. The worst: **the master silently discards a sensor's entire reading
whenever that sensor's battery is low**, because the low-battery message type is
handled by neither branch of the receive dispatch. Close behind, the master
reads a *dynamic* payload length that was never enabled (which can make the
radio flush good packets), and the boot-time config handshake races a blocking
HTTP call against a 200 ms deadline — so it routinely fails and the sensor
retries up to **1000×**, draining battery.

All findings below are fixed on this branch under a **moderate hardening**
mandate, staged so the master-only fixes are independent of the one coordinated
firmware+master re-flash (the versioned wire format).

---

## Findings

### Critical

**P-01 — Low-battery readings dropped by the master.**
`radio.py` `handlePayload` dispatched only on `DATATYPE_CMD_GETCONFIG` (6) and
`DATATYPE_SENSORDATA` (0). A `DATATYPE_SENSORDATA_BATTERYALERT` (1) packet —
which the firmware sends precisely when the battery is low
(`wpw_RXTX.cpp` `HandleTransmitter`) — matched neither branch, so the moisture
reading *and* the low-battery signal were both thrown away, exactly when they
matter most.
**Fix:** both sensor-data types now route through one `handleSensorData` path;
the low-battery condition is parsed (`SensorReading.batteryAlert`) and logged.
*Note:* the alert is not yet persisted — `SensorData` has no such column — but
the reading (incl. voltage) is now saved. A persisted battery-alert field is a
backend follow-up (see `TODO.md`).

### High

**P-02 — Dynamic payload size read while dynamic payloads are disabled.**
`radio.py` called `getDynamicPayloadSize()`, but neither end ever called
`enableDynamicPayloads()`. With static payloads that width is undefined and, if
>32, makes RF24 flush the RX FIFO — intermittent dropped packets. The firmware
read fixed sizes, so the two ends disagreed on framing.
**Fix:** both ends now pin a fixed payload size (`setPayloadSize(PAYLOAD_SIZE)`,
= 8) and the master reads exactly that many bytes.

**P-03 — Racy config handshake + 1000× boot retry storm.**
The sensor waited only 200 ms for a config reply, while the master performed a
**blocking HTTP GET** to its own API inside that window before answering (and
skipped it entirely whenever the request arrived while the master was busy in
`actionEngine`). The reply usually missed the deadline, so the sensor timed out
and retried up to 1000× at 1 s intervals on boot, draining battery
(matches audit M-02).
**Fix:** the master keeps an in-memory `ConfigCache` warmed out-of-band
(`refreshConfigCache`, called from the core loop and at startup) and answers a
`GETCONFIG` instantly from memory — the HTTP GET is no longer in the response
window. The sensor's timeout is widened to 500 ms and the boot loop is now a
bounded 5 retries with linear backoff that **falls back to the EEPROM-cached
config** and starts measuring rather than camping.

**P-04 — No length/type validation on the master.**
`PackageSensorData(payload)` ran before any guard and unpacked `data[2:6]`; a
short/garbage frame raised an unhandled exception inside the radio loop, and
`payload` could be referenced unbound.
**Fix:** parsing moved into `protocol.py` helpers that validate version + length
and return `None` (never raise) on bad input; `handlePayload` is wrapped in
`try/finally` so the radio always resumes listening.

### Medium

**P-05 — Fragile, unversioned wire format.**
Both message structs relied on byte-identical memory layout between AVR-GCC and
Python `struct`, with no `packed` attribute, no size assertions, and no version
byte — working only by AVR's natural 1-byte alignment.
**Fix:** a leading `ProtocolVersion` byte on both structs (checked on receive,
mismatches dropped); the C structs are `__attribute__((packed))` with
`static_assert` size checks (`Package`=7, `ConfigurationPackage`=6) that fail
the build on drift; the Python `struct` formats (`<BBBf`, `<BBHB?`) mirror them.

**P-06 — nRF24 pipe-0 used for a sensor.**
The master bound sensor 1 to hardware reading **pipe 0**, the pipe RF24 reuses
for the auto-ACK address whenever it transmits. (Modern RF24 restores pipe-0's
RX address on `startListening()`, so this may be benign with the installed
version — but the safe pattern costs nothing.)
**Fix:** pipe 0 is reserved for the ACK/writing address; channels map 1:1 onto
reading pipes 1..N. This makes the **5-sensor ceiling explicit** (6 pipes − 1
reserved), reconciling the prior audit's 6-vs-5 confusion: a bidirectional link
on this radio tops out at 5 sensors.

**P-07 — FIFO drain kept only the last frame.**
Both ends looped reading the RX FIFO but retained only the final payload; up to
two earlier queued frames were silently lost.
**Fix:** the master now drains the whole FIFO and processes every frame, each
with its own pipe/channel.

### Hardening also applied
- Explicit `setRetries(5, 15)` on both ends for deterministic auto-ACK behavior.
- `REQUEST_TIMEOUT` on every master→API HTTP call, so a hung API can't stall the
  radio loop (the radio is not listening while a request is outstanding).

---

## Architecture note

The pure wire-format logic now lives in `code/master/core/protocol.py` —
dependency-free (stdlib `struct` only), so it is unit-tested on any machine the
same way the pump controller is, without `pyrf24`/`numpy`/GPIO. `radio.py` is a
thin driver over it. The firmware remains the source of truth for the byte
layout; `protocol.py`'s format strings and the firmware's `static_assert`s pin
the two together.

## Verification
- **Master:** `cd code/master && python -m pytest core/tests/test_protocol.py`
  (9 cases: battery-alert parsed, malformed frames safe, version drop, config
  round-trip, pinned sizes, channel↔pipe mapping, config cache).
- **Firmware:** `cd code/sensor && pio run` — builds for the ATtiny84 target;
  the `static_assert`s confirm the struct sizes match the master.
- **On hardware:** flash one sensor and watch the master log — a low-battery
  reading is now saved; the config handshake completes on the first attempt
  (no boot retry storm; EEPROM fallback if the master is busy); no RF24
  FIFO-flush warnings.

## Follow-ups (not in this change)
- Persist the low-battery flag (add a `SensorData`/`Channel` column + migration)
  so P-01's alert is stored, not just logged.
- Remove the legacy `#ifdef RX` firmware receiver (separate session — `TODO.md`).
- Optional: periodic (not boot-only) config refresh on the sensor so config
  edits reach a node without a reboot.

## Rollout — coordinated flash required
As implemented, the master and sensors are **not** backward-compatible: this
change bundles the `ProtocolVersion` byte and the fixed 8-byte payload size, so
the master and every sensor must be flashed together. The break is clean, not
corrupting:
- A node still on the old firmware uses the nRF24 default 32-byte static payload
  while the master now expects 8, so the hardware CRC fails → no auto-ACK → the
  old node sees `TX_FAILURE` and the master receives nothing.
- Any frame that did arrive is dropped by the version check (`payload[0] != 1`)
  rather than mis-parsed. No crash, no bad data — the node just goes dark until
  reflashed.

For a ~5-node home fleet a coordinated flash is the simplest path, and the
version check means a missed node fails loudly rather than silently corrupting
data. If a phased rollout is ever needed, the master can be made tolerant by
keeping the legacy 32-byte payload size and accepting both legacy and versioned
frames — with the caveat that a legacy battery-alert frame (type byte = 1)
collides with `PROTOCOL_VERSION = 1` and needs length-based disambiguation.
