# Plan T-003: make the Loops demonstration fail on attempt 1 again

From intent T-003. Base: main @ 01354d5. Status: accepted by Sahidul Shaikh (in session, 2026-11-24).

## Evidence
- Run `development-20261124T043801Z` (rules withheld) passed 20/20 on
  attempt 1. Its recorded prompt holds "YYYY-MM-DD (ISO-8601)" once, in the
  CONSTRAINTS section, not in the withheld contract.
- `aml/build/brief.py:37` `preamble()` always appends every brief
  constraint. `artifacts/brief.json` constraints 9-13 are the detector rule:
  inclusive bounds, credits only, inclusive window, ISO output dates, and the
  values when the rule does not fire.
- `aml/build/orchestrator.py` `WITHHELD_CONTRACT` says exactly those things
  are not provided.

## Change
1. `ProductBrief.preamble(include_constraints=True)`: a flag to leave the
   CONSTRAINTS section out.
2. `build_prompt`: when `withhold_rules` and the phase is a code phase, call
   `preamble(include_constraints=False)`. Comment why. Nothing else changes:
   full-requirements runs and document stages still get every constraint.

Dropping the whole section rather than picking out constraints 9-13 is
deliberate: the brief is re-extracted by stage 0 whenever the requirements
change, and a positional or keyword filter would silently break. The other
constraints (citations, tipping off, cost) say nothing a detector function
needs.

## Order of work
1. Prove it deterministically first: build the withheld prompt and list which
   withheld facts it contains (expected: several).
2. Make the change; build the prompt again (expected: none).
3. Add that as a check in `aml_check_04_build.py`, so a future brief cannot
   reintroduce the leak unnoticed.
4. Three live runs with rules withheld (haiku, as the Loops panel uses), about
   $0.02-0.04 each. Report each run's attempts.
5. Five checks pass.

## Risks
- Attempt 1 might still pass, because the model could read the acceptance
  suite from disk (Claude Code runs in the repository with its default
  tools). If so, stop and report it as a separate finding; do not change the
  tools or working directory without the operator's say.
- Attempt 2 might not close the gap. The loop allows three attempts; report
  what happens.

## Proof
- Withheld prompt: before, the list of leaked facts; after, empty.
- Live runs: attempts per run, with each attempt's pass count, from the run
  records.
- Five checks pass; CI green.
