
# TODO

items from this list tjhat have been implemented are moved to the file `CHANGELOG.md`.

- solve as websocket request to avoid CORS:
    - add new channel / schedule
    - remove
- persist the low-battery flag: `SensorData` has no battery-alert column, so the
  sensor's `DATATYPE_SENSORDATA_BATTERYALERT` is currently only logged (the
  reading itself is saved). Add a field + migration to store it. See
  `docs/audits/2026-06-13 - ProtocolReview.md` (P-01).
