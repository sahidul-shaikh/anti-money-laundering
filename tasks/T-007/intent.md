# Intent T-007: a runbook for demonstrating delivery, and claims that match the record

Author: Sahidul Shaikh. Route: a person's idea. Status: accepted.

## Problem
The delivery chain (intent to merge) has no runbook, so a presenter has to
reconstruct the order, timings and failure handling from memory. And the Loops
panel says the first attempt "fails every time", a stronger claim than the
recorded runs support.

## Proposed outcome
`docs/DEMO_RUNBOOK_DELIVERY.md`: pre-flight, the six beats with measured
timings and costs, the questions a room asks, and what to do when something
goes wrong. The Loops wording says what is expected and points at the record.

## Affected users and systems
Presenters. `docs/`, one sentence in `scripts/ui/builds.js`.

## Constraints
Every figure in the runbook comes from a recorded run or a measured check.

## Acceptance condition
The runbook's figures reconcile to `artifacts/live/runs/`; the console sweep
stays at 18 panels and 0 JavaScript errors.

## Open questions
None.
