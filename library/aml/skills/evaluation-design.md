# Skill: designing an evaluation

Use once there is something to evaluate and before anyone quotes a number.

## Procedure

1. Define the **families** separately: correctness against known outcomes,
   groundedness of cited evidence, robustness against the threat model, and cost.
   A single blended score hides the trade-off you most need to see.
2. For each family, state how it is measured and the **pass threshold**.
3. Prefer measures that are computed over measures that are judged. A cited
   reference either exists in the supplied data or it does not; that needs no
   second model.
4. State how **variance** is separated from a real change. Run the identical
   configuration twice and record how much the answer moves. Compare paired, on
   the same items, and count which way each disagreement went.
5. State the sample size needed to detect the effect you care about.

## What good looks like

- Groundedness is deterministic
- The noise floor is measured, not assumed
- The threshold for "this change helped" is set before the change is made

## Common failures

- Comparing aggregate percentages on small samples
- An LLM judge grading a metric that could have been computed
- Reporting an improvement that is smaller than the run-to-run variance
