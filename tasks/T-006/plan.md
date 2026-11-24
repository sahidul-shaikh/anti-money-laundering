# Plan T-006: rebuild the structuring detector from the requirements

From intent T-006. Status: accepted by Sahidul Shaikh (in session, 2026-11-24).

## Files that change
`artifacts/builds/aml-alert-investigator/src/detector.py` and
`tests/test_detector.py`, written by the build loop. Nothing else.

## Order of work
1. Builds / Loops: run the implementation stage with the rules withheld.
   Attempt 1 is expected to fail on the withheld conventions; the acceptance
   suite names what failed; later attempts are written against that feedback.
2. If the loop passes, Builds / Delivery: deliver the latest passing run
   under T-006. If it refuses after three attempts, nothing is delivered and
   the run record says why.
3. A human reviews the pull request and approves it on GitHub.

## Risks
- The loop can refuse (one of three runs did in T-003). Then run it again;
  each run is recorded either way.

## Proof
The run record under `artifacts/live/runs/`, the commit trailers equal to it,
both CI checks green, and the human approval on the pull request.
