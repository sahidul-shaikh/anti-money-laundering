# Skill: verifying a threat model against what was built

Use after the implementation exists and before release.

## Procedure

1. Take each threat `T-n` from the specification in turn. Do not start from the
   code - start from the threat, or you will only verify what was built.
2. For each: name the control, state whether it is **implemented**, and give the
   **residual risk** in a sentence.
3. Mark threats with no control as accepted risks, with an owner.
4. List the adversarial **probes** that must run before release, and say which
   execute against the real system and which are declared but not executed.
5. Distinguish a probe that was defended from one that could not be reproduced.

## What good looks like

- Coverage is traceable threat by threat
- Declared-but-not-executed probes say so plainly
- Residual risk is stated even where the control holds

## Common failures

- Reporting a finding that fired once and never reproduced
- Confusing "no control was triggered" with "no attack was possible"
- Verifying the controls that exist rather than the threats that were modelled
