# Intent T-003: make the Loops demonstration fail on attempt 1 again

Author: Sahidul Shaikh. Route: a finding (T-002 run records). Status: accepted.

## Problem
The Loops panel exists to show one thing: with part of the contract withheld,
attempt 1 fails, the acceptance suite says why, and attempt 2 passes. The
brief records attempt 1 failing 8 times out of 8. The last two recorded runs
passed on attempt 1 with the rules withheld, so the demonstration no longer
shows the loop doing anything.

## Root cause (reproduced from the run record)
Withholding replaces the requirements document with a short contract that
says the rule semantics and output conventions "are NOT provided here". But
every prompt also opens with the product brief, whose CONSTRAINTS section
(brief constraints 9-13, extracted from the same requirements) states those
exact semantics, including the YYYY-MM-DD output convention the hidden test
checks. The prompt withholds the rules and then restates them.

## Proposed outcome
When rules are withheld, the code stage's prompt really does not contain
them, so attempt 1 has to guess and the acceptance suite has something to
correct.

## Affected users and systems
`aml/build/orchestrator.py`, `aml/build/brief.py`. The full-requirements path
and every other stage are unchanged.

## Constraints
- Do not edit the brief itself: it is the human's requirements and is right.
- Do not change what Claude Code inherits (no `--tools`, no working-directory
  change); the operator asked for that to stay.
- Claims stay measured: report how many runs failed on attempt 1, not "always".

## Acceptance condition
A withheld prompt contains none of the withheld rules (checked
deterministically), and live runs with the rules withheld fail attempt 1 and
pass on a later attempt.

## Open questions
None.
