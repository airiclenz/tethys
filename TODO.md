
# TODO

items from this list tjhat have been implemented are moved to the file `CHANGELOG.md`.

- silent phase calculation is not based on UTC but local time --> needs fixing
- solve as websocket request to avoid CORS:
    - add new channel / schedule
    - remove
- implement sensor data / action log views
- remove the legacy Arduino `#ifdef RX` receiver from `code/sensor` (it is
  superseded by the Raspberry Pi master). Collapse `wpw_RXTX.cpp`/`wpw_RXTX.h`
  to the TX path only and drop the `RX` build env. Separate session.
- persist the low-battery flag: `SensorData` has no battery-alert column, so the
  sensor's `DATATYPE_SENSORDATA_BATTERYALERT` is currently only logged (the
  reading itself is saved). Add a field + migration to store it. See
  `docs/audits/2026-06-13 - ProtocolReview.md` (P-01).
- TypeScript cleanup: the frontend is effectively a no-strict codebase. `tsc -p
  web/static/ts/tsconfig.json` reports many pre-existing type errors (implicit
  any, possibly-null) across schedule.ts, tool.ts, websocket.ts, channel.ts,
  common.ts, templatter.ts. JS still emits (noEmitOnError is off), so it's
  non-blocking, but a clean build would mean annotating types / null-guards and
  enabling stricter compiler options. Not introduced by the API-key work.
