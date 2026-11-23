# Skill: model risk documentation

Use before a model-risk reviewer sees the system. Write for a reader whose job
is to refuse it.

## Procedure

1. **Intended use.** The one function this is approved for, stated narrowly, and
   the uses it is explicitly not approved for.
2. **Limitations.** Where it is known to be weak, in what conditions, and what
   data that conclusion rests on. A limitations section with nothing
   uncomfortable in it will not be believed.
3. **Data lineage.** Where the evaluation data came from, what is real, what is
   synthetic, and why synthetic data was needed.
4. **Performance measurement.** The metrics, the sample, the variance, and the
   date measured.
5. **Ongoing monitoring.** What is watched in production, at what cadence, and
   the threshold that triggers review.
6. **Withdrawal.** The conditions under which the model must be taken out of use,
   and who decides.

## What good looks like

- A reviewer can find the answer to "what would make you stop using this"
- Synthetic data is labelled wherever a number depends on it
- Monitoring thresholds are numeric and tied to the quality floor

## Common failures

- Intended use written broadly to avoid re-approval later
- Limitations that are really strengths in disguise
- No withdrawal criteria, which means there are none
