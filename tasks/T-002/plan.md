# Plan T-002: the factory delivers its own output as a pull request

From intent T-002. Base: main @ 4fd85ca. Status: accepted by Sahidul Shaikh (in session, 2026-11-24).

## How it works today
- `scripts/serve_factory.py:151` `start_run` runs the `development` stage via
  `aml/build/live.py:244` `run_code_phase_live`, which writes the generated
  files into `artifacts/builds/aml-alert-investigator/` and ends with a
  `done` event carrying the loop result (attempts, pass/fail, per-attempt
  cost reported by Claude Code).
- `save_run_summary` (`serve_factory.py:654`) writes that to
  `artifacts/live/<phase>.run.json`. There is no run ID.

## Files that change
| File | Change |
|---|---|
| `scripts/serve_factory.py` | `start_run` mints a run ID (`<phase>-<UTC timestamp>`); `save_run_summary` records it |
| `aml/build/bot.py` (new) | Reads the bot token, refuses unless it resolves to `aml-factory-bot`, gives git and gh the bot identity. Replaces the scratchpad wrapper |
| `aml/build/deliver.py` (new) | Delivery: refuse unless the run passed; temporary git worktree from `origin/main`; copy the final attempt's files; commit as the bot with trailers; push; open the PR; remove the worktree |
| `scripts/deliver.py` (new) | Command: `uv run python scripts/deliver.py --task T-002 [--phase development]` |
| `scripts/check_no_real_data.py` | Find the workbook from the main checkout, so the hook also scans pushes made from a worktree |
| `checks/aml_check_04_build.py` | Deterministic checks: trailers built from a run record; failed run refused; wrong identity refused |

## Commit trailers
```
Task: T-002
Stage: development
Model: <model the run used>
Run-Id: development-20261124T101500Z
Attempts: 2 (1: 19 passed 1 failed; 2: 20 passed)
Cost-USD: 0.0143 (reported by Claude Code)
Verified-By: checks/acceptance/test_detector_contract.py
```

## Order of work
1. Run ID in the server; confirm it appears in `development.run.json`.
2. `bot.py` with the identity guard; prove it refuses a wrong token.
3. Worktree-aware workbook lookup in the scan; prove it still blocks.
4. `deliver.py` + command; deterministic checks in check 04.
5. One real loop run (about 2 minutes, about $0.02), then deliver it.
6. Confirm PR author, commit author, trailers equal the run record, CI green.

## Risks
- A server restart is needed to pick up the run ID (it changes `scripts/`).
- The worktree is created outside the repo folder (system temp) and always
  removed, including on failure.
- Delivering the same run twice: refused if its branch already exists.

## Out of scope (step 5)
The console button and the Delivery panel and rail. This step delivers from
the command line so it can be proven on its own.

## Proof
- Bot-authored PR opened by the command, trailers matching the run record.
- Both CI checks green on it.
- Refusal paths shown: failed run, wrong identity, real data in the push.
- Five checks pass.
