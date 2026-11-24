# Plan T-004: show the delivery chain in the console

From intent T-004. Base: main @ ec281a0. Status: accepted by Sahidul Shaikh (in session, 2026-11-24).

## Stations
Intent, Plan, Build loop, Commit, Pull request, CI, Human approval, Merged.

| State | Meaning | Look |
|---|---|---|
| done | evidence exists | solid tick, link to the evidence |
| running | build loop live, or a CI check in progress | pulsing ring, elapsed time |
| waiting | PR green, no approval yet | amber, "waiting for a human" |
| failed | loop refused, or a check failed | red, one-line reason |
| pending | not reached | hollow |
| override | merged without an approving review | grey "owner override", never a tick |

## Data, all read at request time
| Station | Source |
|---|---|
| Intent, Plan | `tasks/<T>/intent.md`, `plan.md`: status line; author and date from `git log` |
| Build loop | `artifacts/live/runs/<run_id>.json` named by a commit's `Run-Id` trailer; a live run from the server's own run registry |
| Commit | `git log` trailers: Task, Stage, Model, Run-Id, Attempts, Cost-USD |
| Pull request, CI, approval, merge | `gh pr list --json` (author, checks, reviews, merge), matched to a task by its `T-nnn:` title; cached 10 s |

## Files
| File | Change |
|---|---|
| `aml/build/delivery_state.py` (new) | Builds the chain per task from the sources above. Read-only |
| `scripts/serve_factory.py` | `GET /api/delivery`; `POST /api/deliver` calling `aml/build/deliver.py` |
| `scripts/ui/rail.js`, `factory.css`, `factory.html` | The rail: polls `/api/delivery` every 5 s while anything is running or waiting, 30 s otherwise; collapsible; respects reduced motion |
| `scripts/ui/delivery.js`, `library/pillars.json` | Builds / Delivery discipline: all tasks, their chains, commit trailers, PR links, and "deliver latest passing run" with refusal reasons shown as given |
| `checks/aml_check_04_build.py` | Chain derivation from fixed sample data: override detected, waiting detected, unmatched PRs reported |

## Order of work (each step verified before the next)
1. `delivery_state.py` + `GET /api/delivery`. Verify against history: T-001
   merged by owner override (#3, no review); T-002 and T-003 approved (#4,
   #5, #6). Setup PRs #1 and #2 listed as "no task".
2. Delivery panel, static view. Sweep all panels: 0 JS errors, existing
   panels' text unchanged.
3. Rail. Screenshot it on a merged task and on T-004's own open PR (CI
   running, then waiting for a human).
4. Deliver button. Live once, under a demo task whose intent the loop's
   output actually serves - T-006 "rebuild the structuring detector from the
   requirements", intent by the human: run the loop (rail: Build loop
   running), deliver from the console (PR, CI running, waiting), the human
   approves on GitHub, rail shows Merged. Screenshot each state.
5. Five checks pass; CI green.

## Risks
- `gh` latency on every poll: 10 s cache, one `gh pr list` call per refresh.
- Panel count becomes 18; START_HERE and the runbooks say 17. Update those
  lines.
- The cold-load race (T-005) can hit the new panel too; the sweep lands on
  the console first, as in T-001.

## Proof
Screenshots of each station state from real data, the sweep result, check 04
results, and CI on the PR.
