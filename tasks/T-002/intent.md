# Intent T-002: the factory delivers its own output as a pull request

Author: Sahidul Shaikh. Route: a person's idea (handoff brief/06). Status: accepted.

## Problem
When the build loop passes, its code stays in a folder on this machine. To
reach `main` a person has to commit it, push it and open a pull request by
hand, as was done for T-001. The factory generates governed work but does not
deliver it, and nothing ties the code in git back to the run that produced it.

## Proposed outcome
After a passing loop run, one command commits the generated files, pushes a
branch and opens a pull request, all as `aml-factory-bot`. The commit and the
PR carry the run's provenance: task, stage, model, run ID, attempts, measured
cost and the acceptance result. The human approves and merges as before.

## Affected users and systems
The build factory (`aml/build/`), the console server (run ID only), GitHub.

## Constraints
- The factory acts up to the merge gate and never past it: it cannot approve
  or merge.
- A run that did not pass the acceptance suite is never delivered.
- Every figure is measured (cost as Claude Code reports it); nothing estimated.
- Delivery must not touch the person's working checkout.
- The pre-push real-data scan still applies.

## Acceptance condition
One real loop run, delivered by the command, produces a bot-authored PR whose
commit trailers match the run record, with both CI checks green.

## Open questions
None.
