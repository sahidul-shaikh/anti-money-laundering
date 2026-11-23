# Skill: writing a specification with testable acceptance criteria

Use at the point where requirements exist and design has not started.

## Procedure

1. Open with scope, and be explicit about what is **out** of scope. Most
   specification disputes are scope disputes.
2. Describe the interfaces: what arrives, what leaves, in what shape.
3. Write acceptance criteria numbered `AC-1` onward. Each one must be decidable
   by a test or by a reviewer applying a stated rule - never by judgement.
4. For each criterion, state the observable that settles it.
5. Mark any criterion you cannot make testable, and say why, rather than
   softening it until it reads as testable and is not.

## What good looks like

- A criterion reads like an assertion: given this input, this is true of the output
- Thresholds are numeric and the boundary behaviour is stated (inclusive or not)
- Nothing says "appropriate", "robust", "as required" or "best practice"

## Common failures

- Criteria that restate the feature list
- Boundary conditions left implicit, which is where implementations diverge
- Non-functional requirements with no measurement attached
