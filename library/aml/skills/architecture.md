# Skill: architecture for a gated AI component

Use once the specification and threat model exist.

## Procedure

1. List the **components** and give each one a single responsibility you can say
   in a sentence.
2. Trace the **data flow** from the triggering event to the recorded decision.
   Follow one unit of work the whole way through.
3. Mark every **trust boundary** the data crosses, and state what changes about
   the data as it crosses.
4. Place each control from the threat model at a component, and say what happens
   when it fires.
5. Say where the human sits.

## What good looks like

- The boundary across which untrusted external text arrives is explicit and
  named, not implied
- Every threat in the model maps to a component
- A reader can find where a decision is recorded and what would reproduce it

## Common failures

- Boxes with no responsibility, or responsibilities spread across boxes
- Controls described in the abstract rather than placed
- No answer to "what happens when the model is unavailable"
