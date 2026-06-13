

- silent phase calculation is not based on UTC but local time --> needs fixing
- solve as websocket request to avoid CORS:
    - add new channel / schedule
    - remove
- implement sensor data / action log views
- TypeScript cleanup: the frontend is effectively a no-strict codebase. `tsc -p
  web/static/ts/tsconfig.json` reports many pre-existing type errors (implicit
  any, possibly-null) across schedule.ts, tool.ts, websocket.ts, channel.ts,
  common.ts, templatter.ts. JS still emits (noEmitOnError is off), so it's
  non-blocking, but a clean build would mean annotating types / null-guards and
  enabling stricter compiler options. Not introduced by the API-key work.