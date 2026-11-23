# AML Alert Triage Agent — Deployment Runbook

## TELEMETRY CONTRACT

The following signals must be live, dashboarded, and alerting **before** the release gate opens. No signal in this table may be "added post-launch" — if it is not emitting, the release does not ship.

| # | Signal | Source | Granularity | Alert threshold |
|---|---|---|---|---|
| T-1 | Disposition distribution (4-way counts: `CLOSE_NO_ACTION`, `ESCALATE_ANALYST_REVIEW`, `ESCALATE_SAR_RECOMMEND`, `ESCALATE_INSUFFICIENT_DATA`) | Response log, per-request | 15 min rolling | `ESCALATE_SAR_RECOMMEND` rate drifts >50% from the 7-day trailing baseline (either direction) |
| T-2 | `ESCALATE_INSUFFICIENT_DATA` rate | Response log | 15 min rolling | >15% of volume (indicates upstream context pipeline degradation, not model degradation) |
| T-3 | Off-schema / parse-failure rate on `AlertTriageResponse` | Serialization layer | Per-request | >0.1% in any rolling 15 min window |
| T-4 | Citation resolution rate (does every cited row/field exist in the supplied `TaggedAlertContext`) | C-5/C-6 groundedness verifier, sampled 100% in production (not the n=50 sample used at functional test) | Per-request | Any single unresolved citation on an `ESCALATE_SAR_RECOMMEND` response pages on-call immediately; <99.5% resolution overall in any 1-hour window pages on-call |
| T-5 | Verbatim memo/counterparty text length in `rationale` | Response log | Per-request | Any response >140 cumulative characters is a hard schema violation — alerts as a bug, not a drift |
| T-6 | PII pattern hits in output fields (SSN/PAN/DOB/routing/address regex scan) | Output scanner, 100% of traffic | Per-request | Any hit (>0) pages on-call immediately — this is a stop-ship class event, not a rate |
| T-7 | Confidence score distribution and null rate | Response log | 15 min rolling | Any null; or p50 confidence drops >0.15 from 7-day baseline |
| T-8 | Latency (p50/p95/p99) end-to-end | Request/response log | 5 min rolling | p95 >8s or p99 >15s |
| T-9 | Transaction-history truncation rate (alerts with >500-row history where rows were dropped) | Input pipeline | 15 min rolling | Report-only at launch (no numeric gate — see Known Gap G-1 below); must be visible so on-call can correlate with disposition anomalies |
| T-10 | Human override rate: analyst disposition vs. model disposition, by direction (model→analyst upgrade severity, model→analyst downgrade severity) | Case management system join, daily batch | Daily | Downgrade-of-`ESCALATE_SAR_RECOMMEND` rate >5% of that disposition's daily volume |
| T-11 | SAR-recall proxy: of alerts analysts ultimately file a SAR on, what fraction the model flagged as `ESCALATE_SAR_RECOMMEND` or `ESCALATE_ANALYST_REVIEW` (i.e., did not silently close) | Case management system join, daily batch, lagged ~5 business days for filing decisions | Daily | Any single missed SAR filing where the model returned `CLOSE_NO_ACTION` is a **mandatory individual review**, not a statistical event |

**Known gap at launch (G-1):** functional test (AC-7, AC-8) found no numeric SAR-recall threshold defined upstream, and the 500-row history truncation/selection algorithm is undocumented. T-9 and T-11 ship as monitoring-only telemetry to partially compensate for this gap. Release under this condition requires an explicit, time-boxed model-risk sign-off (see ROLLBACK, condition R-6) — it is not a silent acceptance of the gap.

All eleven signals must show non-zero, sane data in the pre-production (shadow/canary) environment for a minimum of 5 consecutive business days before the production release gate opens.

---

## ROLLBACK

### Rollback triggers (any one is sufficient — no judgment call required to initiate)

| # | Trigger | Detection | Action |
|---|---|---|---|
| R-1 | PII appears in any output field (T-6 > 0) | Automated, real-time | Immediate automatic rollback (kill-switch), no human approval needed to execute; human notified simultaneously |
| R-2 | Off-schema response rate >1% in any 15-min window (10x the T-3 alert threshold) | Automated | Immediate automatic rollback |
| R-3 | Confirmed missed SAR filing traced to a `CLOSE_NO_ACTION` or `ESCALATE_INSUFFICIENT_DATA` disposition that should have escalated | Manual, via T-11 daily review or analyst escalation | Rollback within 4 business hours of confirmation, pending on-call lead + model risk officer joint decision |
| R-4 | Citation fabrication confirmed on a production `ESCALATE_SAR_RECOMMEND` response (T-4 page) | Automated page, human-confirmed | Rollback within 1 hour of confirmation |
| R-5 | Disposition accuracy on a rolling production sample (weekly re-score against analyst-confirmed outcomes) drops below the 0.90 warning band carried over from E-1 | Manual, weekly batch job | Rollback within 1 business day; if below 0.85, immediate rollback |
| R-6 | Model-risk-imposed time box on the G-1 gap expires without a resolved SAR-recall threshold | Calendar, tracked by model risk officer | Scheduled rollback to prior disposition logic or human-only triage, no incident required to trigger — this is a planned expiry, not a failure |

### Rollback procedure

1. **Declare.** On-call engineer or model risk officer declares rollback, states the trigger ID (R-1 through R-6), timestamps the declaration.
2. **Revert serving.** Flip the model-serving flag to the last known-good pinned model version (version pin is recorded in the deployment manifest at every release; rollback is a config change, not a redeploy — target time-to-revert is <5 minutes for R-1/R-2/R-4, <1 hour for R-3/R-5).
3. **Freeze the case queue.** Any alert disposed by the agent in the 24 hours preceding a confirmed R-1, R-3, or R-4 event is flagged for mandatory analyst re-review before case closure stands. This is a queue freeze, not a re-run — do not re-score retroactively with the reverted model, since that creates an unauditable second opinion.
4. **Notify.** Model risk officer, AML compliance lead, and engineering on-call lead notified within 15 minutes of declaration, regardless of trigger. Regulatory notification obligations (if any) are assessed by compliance, not engineering — engineering's job is timestamped facts, not a judgment on reportability.
5. **Root cause before re-release.** No re-release to the rolled-back version until root cause is identified and a corresponding telemetry signal (new or tightened) would have caught it. "It passed re-test" is not sufficient; the gap in detection must be closed first.
6. **Post-incident record.** Written incident record within 3 business days: trigger, timestamp, time-to-revert, number of alerts affected, root cause, telemetry change made. Filed with model risk documentation, not just engineering tickets — this feeds the next SR 11-7 review cycle.

---

## RUNBOOK

### On-call response to a degraded (not fully down) agent

**Severity classification on page:**

- **SEV-1** — any PII trigger (R-1), off-schema spike (R-2), or confirmed missed SAR (R-3/R-4). Page on-call immediately, 24/7, ack SLA 10 minutes.
- **SEV-2** — T-2, T-7, T-8 threshold breaches; elevated `ESCALATE_INSUFFICIENT_DATA` or latency. Page during business hours, ack SLA 1 hour; after-hours, next business day unless compounding with SEV-1 signals.
- **SEV-3** — T-9, T-10 drift without a confirmed miss. Logged, reviewed at next daily standup, no page.

**SEV-1 response steps:**

1. Ack the page, open an incident channel, post trigger ID and first-observed timestamp.
2. Check T-6 (PII) and T-3 (schema) dashboards first — these are binary and fastest to confirm or rule out.
3. If confirmed: execute ROLLBACK procedure immediately. Do not attempt a hot-fix in production.
4. If not confirmed (false page): check for an upstream data contract change (new field, renamed field, encoding change in the `TaggedAlertContext` feed) — this is the most common root cause of a schema/citation false alarm. Compare against the last known-good context schema version.
5. Escalate to the model owner if root cause is not identified within 30 minutes.

**SEV-2 response steps:**

1. Correlate the triggering metric against T-9 (truncation rate) and recent context-pipeline deploys — most SEV-2 events trace to upstream data issues (KYC feed lag, screening score pipeline delay) rather than the model itself.
2. If traced to upstream data: route to the owning data pipeline team, do not roll back the agent.
3. If traced to the model: open a tracked ticket, do not page further unless it compounds into a SEV-1 signal within the same incident window.

**Degraded-mode fallback:** if the agent is rolled back or disabled, all alerts route to 100% human analyst triage (no automated disposition). This is the designed fail-safe state — it must be load-tested annually (see CADENCE) to confirm the analyst queue can absorb full volume without a backlog exceeding 24 hours.

**Explicit non-goals of this runbook:** this runbook does not cover model retraining procedures, upstream KYC/screening data pipeline incidents in isolation (those have their own runbook), or case-management system outages — only agent-specific degradation.

---

## CADENCE

| Review | Frequency | Owner | Content |
|---|---|---|---|
| Telemetry dashboard review | Daily | On-call engineering lead | T-1 through T-9, prior 24h |
| SAR-recall proxy review (T-11) | Weekly | Model risk officer + AML compliance lead | All `CLOSE_NO_ACTION`/`ESCALATE_INSUFFICIENT_DATA` dispositions on alerts later filed as SARs |
| Override-rate review (T-10) | Weekly | Model owner | Analyst disagreement patterns, direction and magnitude |
| Disposition accuracy re-score against analyst-confirmed outcomes | Weekly | Model owner | Rolling sample, feeds R-5 trigger |
| Full SR 11-7-aligned model risk review | Quarterly | Model risk officer | Accuracy trend, fabrication-rate trend, incident log since last review, G-1 gap status |
| Degraded-mode (human-only) load test | Annually, or after any >20% sustained volume increase | Engineering + AML operations | Confirms analyst queue absorbs 100% volume within 24-hour backlog target |
| G-1 gap resolution checkpoint (SAR-recall threshold, truncation algorithm documentation) | Fixed deadline, no later than 90 days post-launch | Model risk officer | Pass/fail; failure triggers R-6 scheduled rollback |

Every review in this table produces a written artifact (dashboard snapshot, memo, or incident log excerpt) retained for the model's full production lifetime plus the regulatory retention period applicable to SAR-adjacent decisioning — this is a model risk documentation requirement, not an engineering convenience.