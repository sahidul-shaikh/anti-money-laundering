# Intent T-004: show the delivery chain in the console

Author: Sahidul Shaikh. Route: a person's idea (handoff brief/06). Status: accepted.

## Problem
The factory now performs governed delivery - intent, plan, build loop, commit
with provenance, bot-authored pull request, CI, human approval, merge - but
none of it is visible in the console. To show it today, a presenter switches
between a terminal, GitHub and the console, and the audience loses the thread.

## Proposed outcome
1. A side rail, visible on every console page, showing the current task's
   chain as stations, with the running one animated and "waiting for a human"
   clearly distinct.
2. A Builds / Delivery panel listing every task with its full chain and links
   to the evidence, and a button that delivers the latest passing run.

## Affected users and systems
Presenters and their audience. `scripts/ui/`, `scripts/serve_factory.py`, a
new read-only state module in `aml/build/`, `library/pillars.json`.

## Constraints
- Every station reads real state: git, GitHub, the run records, the live run
  stream. Nothing advances on a timer; no percentage bars.
- The console has no approve or merge button. Approval happens on GitHub.
- Merges that bypassed review are shown as such, not as approvals.
- No real customer data on screen beyond what the console already shows.

## Acceptance condition
The rail and panel show the true state of T-001 to T-003 from history, and
follow a real run through running, waiting for a human, and merged.

## Open questions
None.
