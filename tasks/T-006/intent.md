# Intent T-006: rebuild the structuring detector from the requirements

Author: Sahidul Shaikh. Route: a person's idea (the standing demonstration). Status: accepted.

Delivery: factory

## Problem
The structuring detector (`artifacts/builds/aml-alert-investigator/src/detector.py`)
is the one piece of code the factory writes. To show governed delivery end to
end, the factory needs a task its build loop genuinely serves, so the record
in git says what was asked for and what was delivered against it.

## Proposed outcome
The factory rebuilds the detector with part of the contract withheld, the
hidden acceptance suite corrects it, and the passing run is delivered as a
pull request by aml-factory-bot for a human to approve.

## Affected users and systems
The build loop's implementation stage; `artifacts/builds/aml-alert-investigator/`.

## Constraints
- The detector must pass all 20 tests in
  `checks/acceptance/test_detector_contract.py`, a suite the model never sees.
- Only a passing run is delivered. A run the loop refuses is shown as refused.
- A person approves the pull request on GitHub; the factory cannot.

## Acceptance condition
A delivered pull request whose commit trailers match the run record, both
CI checks green, approved and merged by a human.

## Open questions
None. This task is repeatable: each demonstration delivers a fresh run
against it.
