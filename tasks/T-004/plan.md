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

## Implementation notes (departures from this plan)
- **GitHub query limit.** One `gh pr list` with commits and authors for 100
  PRs exceeds GitHub's 500,000-node ceiling. Limited to the 30 most recent
  PRs, stated in the code.
- **A run ID alone is not a loop run.** T-001 carried a run ID for an
  interactive session; the first chain showed it as a loop run with "?"
  values. A station is "done" only when the run's record exists.
- **"CI failed" while CI was running.** GitHub reports an in-progress check's
  conclusion as "" rather than null; the rail read that as failure. The check
  04 sample had used null, so it did not catch it. Proved the realistic sample
  fails on the old logic, then fixed both.
- **Waiting time** is measured from the last check going green, not from the
  PR opening.
- **No default task** in the deliver picker, so a careless click cannot put a
  false record in git.
- **Deliveries carry their run record.** The server saves every run under
  `artifacts/live/runs/<run_id>.json`; delivery commits it with the generated
  files and refuses a run whose record is missing. Closes the T-002 gap.
- **Demo task T-006** added (intent by the human) so live deliveries are filed
  against a task the loop's output actually serves.
- `artifacts/live/development.run.json` is now the T-006 demonstration run,
  so the Loops panel's recorded card shows it.

## Result
- History read true: T-001 owner override; T-002, T-003 approved; setup PRs
  #1 and #2 shown as having no task.
- 18 panels, 0 JavaScript errors; the 17 existing panels unchanged except the
  Builds counter.
- Live, from the console: run `development-20261124T070341Z` (attempt 1
  19/20, attempt 2 20/20, $0.01534) delivered by the Delivery panel's button
  as #8 with its run record; the rail showed the loop running, CI running,
  waiting for a human, then all eight stations done after the human approved
  and merged.
- Check 04: delivery refusals, chain derivation (override, waiting, running,
  failed, record required, live loop); five checks pass.
