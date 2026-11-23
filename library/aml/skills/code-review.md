# Skill: reviewing an AI component

Use after implementation and evaluation design exist.

## Procedure

1. Read the contract, then the code, then the tests - in that order.
2. For each finding give a **severity** and a specific remedy. "Consider
   improving" is not a finding.
3. Check the boundaries against the specification yourself. Do not trust that a
   passing test suite covers them; check what it asserts.
4. Check the failure paths: what happens on malformed input, on an empty
   collection, on a provider error.
5. Say plainly what you would **block** on, and what you would let through with a
   follow-up.

## What good looks like

- Findings reference a line and a clause of the specification
- The blocking set is small and defensible
- A reviewer's own uncertainty is stated rather than hidden

## Common failures

- Style comments crowding out correctness ones
- Accepting tests as evidence without reading them
- No distinction between what blocks release and what does not
