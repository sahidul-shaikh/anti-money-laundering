# Intent T-010: show the intent and the plan, and accept a plan before every build

Author: Sahidul Shaikh. Route: a person's idea (demonstration review). Status: accepted.

## Problem
The demonstration started at the build loop. Intent and Plan were green ticks
with nothing to read, and nothing happened at either of them, so the story
skipped the stage the playbook says comes first.

## Proposed outcome
- The intent and the plan can be opened and read in the console.
- Before every build, the factory drafts a plan for that run; a person reads
  it and accepts it, and accepting it is what starts the build.
- The acceptance is recorded under the person's GitHub login and travels with
  the delivered pull request.

## Constraints
- The plan must not reveal the withheld rules.
- "Accept plan" replaces the run button on 04 Loops.
- Nothing is built without an accepted plan.

## Acceptance condition
A live cycle from the console: plan drafted, accepted, built, delivered, with
`Plan-Accepted-By` and the plan file in the delivered PR.

## Open questions
None.
