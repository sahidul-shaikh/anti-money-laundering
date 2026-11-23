# Skill: deployment runbook for a gated AI component

Use last, before release.

## Procedure

1. State the **telemetry contract**: what must be live before release. If the
   telemetry is not there, the release does not happen.
2. State the **rollback trigger** as a numeric condition, and the procedure as
   steps someone can follow at three in the morning.
3. Write the **runbook** for a degraded component: what the symptoms look like,
   what to check first, and what to do while the cause is unknown.
4. State the **review cadence** and who attends.
5. Name the person accountable at each step.

## What good looks like

- Rollback is a threshold, not a judgement call
- The runbook assumes the reader is tired and has not read the architecture
- Telemetry is a precondition of release, not a follow-up ticket

## Common failures

- A rollback plan that is "redeploy the previous version" with no trigger
- Monitoring listed without the threshold that makes it actionable
- No cadence, so the first review happens after the first incident
