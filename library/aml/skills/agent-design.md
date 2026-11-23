# Skill: designing an agent loop and graph

Use when the work is more than one model call.

## Procedure

1. State the **goal** in terms of an observable end state, not an activity.
2. Define the **loop**: act, then verify, then decide whether to iterate. The
   verification must come from something the agent does not control - a test
   suite, a schema, a deterministic check. Self-assessment is not verification.
3. State the **stopping condition** and the maximum iterations. A loop that
   cannot give up is a hang.
4. Define the **graph**: nodes, edges, and what travels along each edge. Where
   two nodes do not depend on each other, say so - that is the parallelism.
5. Define the **shared state**: what every node can read, what only one may write.
6. Mark every **human gate**, and say what the human is deciding.

## What good looks like

- The verifier is independent of the actor
- Each iteration receives the verifier's actual output, not a summary
- The graph shows joins, not just a sequence

## Common failures

- A loop with no exit but success
- Feedback that paraphrases the failure instead of passing it through
- Gates that log an approval nobody can withhold
