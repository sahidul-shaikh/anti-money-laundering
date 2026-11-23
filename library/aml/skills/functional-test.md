# Skill: tracing acceptance criteria to tests

Use after implementation, before deployment.

## Procedure

1. List every acceptance criterion from the specification, by identifier.
2. For each, name the test that covers it and record the **result**.
3. Mark any criterion that is **not covered**, explicitly. An absent row reads as
   an oversight; a row marked uncovered reads as a decision.
4. Where a criterion is partly covered, say which part.
5. Record what was run, when, and against which version.

## What good looks like

- Every `AC-n` appears exactly once
- Uncovered criteria are visible, not omitted
- The trace is reproducible from what was recorded

## Common failures

- Coverage claimed because a test exists in the same area
- Criteria silently dropped when they turned out to be hard to test
- Results recorded with no version attached
