# Plan T-008: the rail follows the chosen task, and runs are filed once, correctly

From intent T-008. Base: main @ 4978222. Status: accepted by Sahidul Shaikh
(in session, 2026-11-24; asked to proceed without a separate review).

## Causes
- Focus was "newest task with no merged PR"; once every task had one, it fell
  back to the last task (T-007). The Delivery picker never told the rail.
- The picker listed every accepted task; delivery checked only that the task
  had an intent.
- The duplicate check matched task and run together, so one run could be
  delivered under two tasks.

## Change
| File | Change |
|---|---|
| `aml/build/delivery_state.py` | `snapshot(focus=)`; default focus prefers a task with an open PR; tasks carry `deliverable` (intent line `Delivery: factory`); a live run, or a run newer than the task's last PR, starts a new cycle for a deliverable focus task only |
| `scripts/serve_factory.py` | `GET /api/delivery?focus=` |
| `aml/build/deliver.py` | `check_task`: refuse tasks without `Delivery: factory`; refuse a run already delivered under any task |
| `scripts/ui/rail.js`, `delivery.js` | Rail task selector (remembered per browser); the Delivery picker lists deliverable tasks only and moves the rail |
| `tasks/T-006/intent.md` | `Delivery: factory` |
| `checks/aml_check_04_build.py` | Cycle and deliverability checks |

## Proof
- Rail follows its own selector (T-003) and the Delivery picker (T-006), and
  remembers the choice after a reload; 18 panels, 0 JavaScript errors.
- Deliver picker offers T-006 only. Delivering to T-001: refused. Re-delivering
  run `094438Z`: refused, naming the earlier branch. No PR created by either.
- Check 04: 6 new checks pass, locally and in CI mode.

## Left for the owner
PR #12 files the detector under T-001. Closing it unmerged restores T-001's
true record (owner override on #3).
