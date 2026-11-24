# Intent T-008: the rail follows the chosen task, and runs are filed once, correctly

Author: Sahidul Shaikh. Route: a finding (first demonstration run). Status: accepted.

## Problem
In the first demonstration the rail always showed T-007, whichever task was
selected. The deliver picker offered every accepted task, so a run was
delivered under T-001 (PR #12), a task that never asked for the detector; the
same run was then delivered again under T-006 (PR #13).

## Proposed outcome
- The rail shows the task the presenter chose, from its own selector or the
  Delivery panel's picker.
- Only a task that declares it accepts factory deliveries can receive one.
- A run is delivered once.
- For a repeatable task, a new run starts a new cycle on the rail instead of
  showing the previous PR as this run's progress.

## Constraints
Every station still reads real state; nothing on a timer.

## Acceptance condition
The rail follows both selectors; delivering to T-001 and re-delivering a run
are refused; chain checks cover cycles and deliverability.

## Open questions
None.
