# Plan T-010: show the intent and the plan, and accept a plan before every build

From intent T-010. Base: main @ c83bfd8. Status: accepted by Sahidul Shaikh
(in session, 2026-11-24: options A and B as one task; Accept on 04 Loops;
acceptance recorded in the delivered PR).

## Change
| File | Change |
|---|---|
| `aml/build/planning.py` (new) | Planning prompt from the task's intent and the same contract the build gets (withheld when the rules are withheld) |
| `aml/build/orchestrator.py` | `build_prompt(plan=)`: the accepted plan goes into the build prompt |
| `scripts/serve_factory.py` | `PLAN` record; `POST /api/plan` drafts in the background; `GET /api/plan`; `POST /api/plan/accept` records the person's `gh` login and starts the build; `GET /api/doc` serves a task's intent or plan, or this run's plan; run records keep the plan |
| `aml/build/deliver.py` | `Plan` and `Plan-Accepted-By` trailers; the plan delivered as `artifacts/live/runs/<run_id>.plan.md`; PR body names who accepted it |
| `aml/build/delivery_state.py` | Plan station follows the run's plan (drafting, waiting for a human, accepted, failed), then the delivered trailer; a plan starts a new cycle; Intent and Plan carry a document to open |
| `scripts/ui/rail.js`, `factory.css` | Document viewer for any station with a document |
| `scripts/ui/builds.js` | 04 Loops: "draft a plan for this run", then "accept plan - start the build" |
| `docs/DEMO_RUNBOOK_DELIVERY.md` | Beat 1 in the console; Beat 2 is the plan and the first human gate |
| `checks/aml_check_04_build.py` | 7 plan checks |

## Proof
- The planning prompt contains none of the 8 withheld facts (also a check).
- Live, from the console, run `development-20261124T182426Z`: plan drafted in
  13.3 s ($0.0059), Plan pulsed then waited; accepted; attempt 1 failed
  (17/20), attempt 2 passed; Commit and PR pulsed; PR #19 by aml-factory-bot
  with the plan file, `Plan-Accepted-By: sahidul-shaikh` and the PR body line.
- The accepted plan did not remove the first-attempt failure.
- 18 panels, 0 JavaScript errors; five checks pass.
