# Skill: threat modelling an AI system

Use before any code exists. A threat model written after implementation
documents what was built; written before, it constrains what gets built.

## Procedure

1. Draw the trust boundaries first. For each input, ask: **who writes this?**
   Anything written by a party outside the institution is attacker-controlled.
2. Enumerate threats `T-1` onward. For each: the surface, the adversary's goal,
   and what they gain.
3. For each threat, name the control and say whether it is **architectural** or
   **detective**. Prefer architectural: a control that makes an attack
   structurally impossible beats one that recognises it.
4. State the residual risk honestly, including threats you are accepting.

## The AML threat library

Work through these before inventing others:

- **Injection through attacker-controlled free text.** Payment reference and
  remittance fields are written by whoever sent the payment and travel into the
  prompt unchanged. Treat them as evidence framed as data, never as instruction.
- **Tipping off.** Disclosing that a party is under a suspicious activity report
  is a criminal offence (31 U.S.C. 5318(g)(2)). Must be impossible, not discouraged.
- **Excessive agency.** An agent that can close an alert is a laundering tool if it
  can be steered. Destructive scopes must be ungrantable, not merely ungranted.
- **Threshold inference.** Repeated near-boundary activity maps where the rule
  fires without the attacker ever reading the specification.
- **Identifier leakage.** Telemetry that carries account numbers or tax
  identifiers turns a metrics store into a copy of the customer master.
- **Evidence fabrication.** A cited transaction that does not exist is a
  correctness defect with regulatory consequences, not a formatting issue.

## Common failures

- Listing threats without controls, or controls without owners
- Treating prompt injection as something a filter solves
- Omitting the threats you have decided to accept
