# Handoff — Tethys pump-control safety module (phase 1)

**Date:** 2026-06-13
**Branch:** `fix/pump-control-safety-module` (off `main`)
**Commit:** `f992d87` — "Add pump-control safety module (audit candidate 1, phase 1)"
**Status:** Implemented, committed, **16 tests passing** off-hardware. NOT pushed. NOT yet tested on the Pi.

---

## What this work is

Acting on the two audits (`docs/audits/2026-06-11 CodeAudit.md`,
`docs/audits/2026-06-11 ArchitectureReview.html`), we started the architecture
review's **top recommendation — "one pump-control module owns the GPIO"** —
split into phases. **Phase 1 (this commit)** delivers the flood-safety module +
first test seam. See the full approved plan at
`/root/.claude/plans/eager-cooking-puzzle.md` (do not duplicate it here).

Scope/decisions are in the commit message and plan; the code is the diff
(`git show f992d87`). This doc only captures what those artifacts don't.

## Key decisions made with the user (not obvious from the diff)

1. **RX firmware stays.** The audit's M-01 suggested removing/quarantining the
   `#ifdef RX` Arduino code as a "rival controller." The user corrected this:
   **RX is the battery-powered moisture-sensing receiver and must stay.** Treat
   the Pi master and sensor nodes as a permanent pair. Do not action M-01.
2. **Phase 1 = safety module only**, chosen over doing all of candidate 1 at once.
   We kept **per-operation GPIO** (open/claim/write/close per action) so the new
   core module coexists with the Django API still driving pins. This deliberately
   leaves **H-01 (two GPIO owners) open**.
3. **C-01 is mostly a false alarm** (confirmed live): `handleCoreActivities` is a
   sync `while True`, so it blocks *inside* the `create_task` argument — no
   TypeError, watering/radio DO run; only `fan.control_fan()` never gets
   scheduled. This phase did NOT touch that; the async fix is deferred.

## Immediate next step (user is doing this)

User is pulling the branch onto the **actual Raspberry Pi hardware** to test.
- They may ask to **push** the branch first (`git push -u origin
  fix/pump-control-safety-module`) — offered, not yet done.
- On-Pi checklist was given in-chat: core boots + drives lines LOW; auto-water
  stops at `pumpDurationSeconds`; flood guard caps at `MAX_PUMP_SECONDS` (300);
  restart-mid-pump leaves line off; API manual activate/deactivate still works
  with no `GPIO_BUSY`.
- **Behavior change to confirm acceptable on hardware:** pumping is now
  non-blocking (timer-driven) and `max_concurrent=1` defers a 2nd simultaneous
  channel to the next loop pass. Reverting to concurrent is a one-line default.

If the Pi test fails, expect to **fix forward** on this branch.

## Phase 2 (next planned chunk — NOT started)

Make the core the single GPIO owner (closes H-01 + the unauth-API pump flood
combo). Per the design agents' findings, this means:
- New `PumpCommand` DB model + migration; API `channel_single_action`
  (`api/tethys_api/views.py`) stops calling `core.channel` and enqueues a command
  instead; remove the `sys.path`/`import core.channel` from views.
- Core drains the queue each loop via new `apiInterface` functions; route the
  scheduled-pump path through the same `pumpController`; switch to a **persistent**
  chip handle (only safe once the API no longer claims lines — coordinated cutover).
- **C-01 async loop** is a co-requisite (otherwise manual activate is up to 30s
  laggy). Recommended transport = **Option A (DB command-queue)**, sequenced
  together with C-01. Then `core/channel.py` can be deleted.

## Other audit items still open (independent, can land in parallel)

Quick wins needing no design (from the ArchitectureReview "hardening note"):
DRF auth + token, `DEBUG=False`, `SECRET_KEY` out of git + rotate, `timeout=` on
all ~12 `requests` calls, `jobs.py` timer-leak, firmware `volatile`/atomic ISR
flags + `millis()` rollover + config-retry cap, silent-phase tz + type-filter fix
(candidate 2), config consolidation (candidate 3), dead-code sweep.

## Environment notes

- Dev box has **no pip/venv**; pytest was installed via `apt-get install -y
  python3-pytest` (7.4.4). Run tests with `python3 -m pytest -q` from
  `code/master/`. No lgpio present — module imports are lazy by design.
- `docs/audits/` is git-ignored (a `.gitignore` lives in it); the audit files are
  present on disk but won't show in `git status`.

## Suggested skills for the next session

- **`verify`** / **`run`** — confirm the core boots and pump auto-off behaves on
  the Pi after pulling the branch.
- **`pr-lifecycle`** — to push the branch and open a PR for phase 1 once
  hardware-tested.
- **`coding-standards`** — when writing the phase-2 changes.
- **`code-review`** — re-run against the branch to confirm the cross-validated
  findings (C-02, 6-vs-5) are resolved and nothing regressed.
- **`grill-with-docs`** / **`improve-codebase-architecture`** — before phase 2, to
  pin the API→core command-queue design (there's no CLAUDE.md/ADRs yet).
