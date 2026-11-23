# Skill: deciding what an agent is shown

Use after the agent design and before implementation. What the agent is given
determines what it can be right about.

## Procedure

1. List every field the agent receives for one unit of work, and for each one
   name its **source system**.
2. List what is deliberately **withheld**, and why. Withholding is a design
   decision and belongs in the record.
3. Identify which fields are **attacker-controlled**. For each, state how it is
   framed in the prompt so that instruction-shaped content arrives as evidence.
4. State what the agent must never be told - anything that would let it decide
   by reading the answer rather than the evidence.
5. State the order of the context, stable content first, so a cache can hold.

## What good looks like

- Provenance for every field
- A clear statement of which fields an adversary can write
- Nothing in the context that encodes the expected answer

## Common failures

- Padding the context with everything available, which lowers accuracy
- Leaking a label, a prior disposition, or a reviewer note
- Treating free text as trusted because it arrived through an internal system
