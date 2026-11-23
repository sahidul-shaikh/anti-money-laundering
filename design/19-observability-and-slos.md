# Observability and Service Levels

| | |
|---|---|
| **Document ID** | AMLI-OBS-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | SRE Lead |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Five layers, not uptime

Availability and error rate answer none of the questions a supervisor asks about
an AI control. These five do, and every figure in them is computed from the
ledger — nothing is asserted in two places (principle P-1).

| Layer | Question | Owner |
|---|---|---|
| **SYSTEM** | Is it up and responding? | SRE |
| **MODEL** | What did it cost, on which models? | SRE + FinOps |
| **AGENT** | Is it grounded, and is it behaving? | Engineering + Security |
| **TRANSACTION** | Is it right? | Model Risk + Investigations |
| **VALUE** | Is it worth running? | Head of Financial Crime Technology |

---

## 2. Metric catalogue

### 2.1 SYSTEM

| Metric | Type | Dimensions | Source |
|---|---|---|---|
| `amli_api_request_duration_seconds` | histogram | route, method, status | API |
| `amli_run_duration_seconds` | histogram | scenario, tier, outcome | `ai_run` |
| `amli_run_total` | counter | status, termination_reason | `ai_run` |
| `amli_queue_depth` | gauge | queue | SQS |
| `amli_queue_oldest_message_age_seconds` | gauge | queue | SQS |
| `amli_ingestion_lag_seconds` | gauge | source_system | watermark |
| `amli_dlq_messages` | gauge | queue | SQS |
| `amli_quarantined_rows_total` | counter | source_system, reason_code | ingestion |

### 2.2 MODEL

| Metric | Type | Dimensions | Source |
|---|---|---|---|
| `amli_model_call_total` | counter | model, tier, status | `model_call` |
| `amli_model_call_duration_seconds` | histogram | model, tier | `model_call` |
| `amli_tokens_total` | counter | model, direction (in/out/cached) | `model_call` |
| `amli_cost_usd_total` | counter | model, tier, scenario | `model_call` |
| `amli_escalation_total` | counter | reason | routing |
| `amli_provider_error_total` | counter | provider, error_class | gateway |
| `amli_budget_utilisation_ratio` | gauge | period | budget guard |

### 2.3 AGENT

| Metric | Type | Dimensions | Source |
|---|---|---|---|
| `amli_groundedness_ratio` | histogram | scenario, tier | `recommendation` |
| **`amli_invented_citation_total`** | counter | scenario, model | `recommendation` |
| `amli_unparseable_total` | counter | model | parser |
| `amli_insufficient_information_total` | counter | reason | runtime |
| `amli_control_check_total` | counter | control_name, phase, outcome | `control_check` |
| `amli_security_event_total` | counter | threat_type, severity | `security_event` |
| `amli_evidence_items_per_run` | histogram | scenario | `run_evidence` |

> `amli_invented_citation_total` is a **defect counter, not a quality metric**.
> Its target is zero and any non-zero value raises a bug, not a tuning task.

### 2.4 TRANSACTION

| Metric | Type | Dimensions | Source |
|---|---|---|---|
| `amli_disposition_total` | counter | disposition, scenario | `recommendation` |
| `amli_decision_total` | counter | outcome, agreed | `decision` |
| **`amli_override_ratio`** | gauge | reason_code, scenario | `decision` |
| `amli_recall` | gauge | dataset_version | evaluation |
| `amli_accuracy` | gauge | dataset_version | evaluation |
| `amli_repeat_agreement` | gauge | dataset_version | evaluation |
| `amli_dispositions_without_human_decision` | gauge | — | control report |

`amli_dispositions_without_human_decision` has a target, a floor and an alert
threshold all equal to **zero**. It is the single number that evidences BR-003.

### 2.5 VALUE

| Metric | Type | Dimensions | Source |
|---|---|---|---|
| `amli_cost_per_alert_gbp` | gauge | scenario | ledger + review time |
| `amli_cost_per_outcome_gbp` | gauge | disposition | ledger |
| `amli_analyst_handling_seconds` | histogram | scenario | workspace |
| `amli_alerts_handled_total` | counter | scenario | `decision` |
| `amli_baseline_delta_gbp` | gauge | — | contract comparison |
| `amli_alert_age_at_disposition_seconds` | histogram | scenario | `alert` |

---

## 3. Service level objectives

| SLI | Definition | SLO | Window | Error budget |
|---|---|---|---|---|
| Reviewer availability | Successful / total requests to the workspace API | 99.9% | 28 days | 40 min |
| Reviewer latency | p95 of interactive reads | ≤ 1.5 s | 28 days | 5% of requests |
| Investigation completion | Runs completing without manual intervention | ≥ 98% | 28 days | 2% |
| Batch timeliness | Daily batch completing in its window | ≥ 99% of days | 90 days | 1 day/quarter |
| Ingestion freshness | p95 ingestion lag | ≤ 30 min | 28 days | 5% |
| Write-back delivery | Delivered within 5 min of decision | ≥ 99% | 28 days | 1% |
| Groundedness | Recommendations with zero invented citations | **100%** | 28 days | **none** |
| Human authority | Dispositions without a human decision | **0** | always | **none** |

Two SLOs have no error budget. They are correctness properties, not reliability
targets, and a single breach is an incident.

### Error budget policy

| Budget remaining | Consequence |
|---|---|
| > 50% | Normal release cadence |
| 10–50% | Reliability work prioritised alongside features |
| < 10% | Feature releases paused; only reliability and security fixes |
| Exhausted | Change freeze until the budget recovers, signed off by the service owner |

---

## 4. Tracing

| Property | Rule |
|---|---|
| Correlation | `trace_id` created at ingestion, propagated through every hop, stored on `ai_run`, emitted on every log line and every provider request |
| Span coverage | Ingestion, evidence capture, rule resolution, render, each guardrail, each model call, parse, ground, persist, write-back |
| Span attributes | `run_id`, `scenario_code`, `tier`, `model_identifier`, `attempt`, `institution_id` |
| **Forbidden attributes** | Party name, account number, transaction reference, amount, any reasoning text |
| Sampling | 100% of runs with a non-`completed` status, 100% with a security event, 10% otherwise |
| Retention | 30 days hot, 1 year archived |

---

## 5. Logging

Structured JSON, one event per line, with an allow-listed field set.

```json
{
  "ts": "2026-11-18T09:14:22.113Z",
  "level": "INFO",
  "service": "agent-runtime",
  "event": "run.completed",
  "trace_id": "4bf92f35…",
  "run_id": "0192f3a9-…",
  "institution_id": "0192a000-…",
  "scenario_code": "SAS10014",
  "tier": "premium",
  "attempts": 2,
  "groundedness": 1.0,
  "cost_usd": 0.0112,
  "duration_ms": 13284
}
```

| Rule | Enforcement |
|---|---|
| No customer data | Allow-listed fields; a logger rejecting unknown keys; automated PII scan on log output fails the build |
| No reasoning text | Reasoning lives in the database under access control, never in logs |
| No secrets | Secret scanner over log output |
| No prompts | Prompts are stored as evidence objects; logs carry only the hash |

---

## 6. Dashboards

| Dashboard | Audience | Content |
|---|---|---|
| **Service health** | SRE, on-call | SLIs against SLOs, error budget, queue depth, DLQ, latency percentiles, provider error rate |
| **Spend** | FinOps, service owner | Cost per alert, per model, per scenario; budget utilisation; escalation rate; projection against the contract |
| **Agent behaviour** | Engineering, Security | Groundedness distribution, invented-citation counter, control-check outcomes, security events by type, insufficient-information rate |
| **Quality** | Model Risk, Investigations | Recall, accuracy, override rate by reason code and scenario, repeat agreement, drift indicators, deviation bands |
| **Value** | Head of Financial Crime Technology | Cost per alert against the GBP 17.00 baseline and GBP 12.00 target, handling time, alert age, volume handled |
| **Supplier** | SRE | Bedrock latency, throttling, quota utilisation — tracked separately because it is outside our control |

---

## 7. Alerting

Every alert has a runbook entry (NFR-070). Alerts without one are deleted, not
tolerated.

| Alert | Severity | Condition | Runbook |
|---|---|---|---|
| Disposition without human decision | **P1** | `amli_dispositions_without_human_decision > 0` | RB-01 — suspend processing, notify MLRO and MRM |
| Audit chain break | **P1** | Daily verification fails | RB-02 — preserve, escalate to Security and Audit |
| Spend cap breached | **P1** | `budget.exceeded` event | RB-03 — confirm cause, raise cap or pause |
| Invented citation in production | **P2** | `amli_invented_citation_total` increases | RB-04 — sample, raise defect, consider rollback |
| Adversarial exploit succeeded | **P2** | Security event severity ≥ high | RB-05 — assess, contain, block release |
| Recall below floor | **P2** | Evaluation gauge below 0.90 | RB-06 — deviation, candidate rollback |
| Override rate above band | **P3** | `amli_override_ratio` > 0.30 for 7 days | RB-07 — failure mining, is it model or reviewer? |
| Batch window missed | **P3** | Batch incomplete at window close | RB-08 |
| Write-back dead-letter | **P3** | DLQ depth > 0 for 30 min | RB-09 |
| Ingestion stalled | **P3** | Lag > 2 h | RB-10 |
| Provider error rate | **P3** | > 5% over 15 min | RB-11 — confirm fallback engaged |
| Quarantine spike | **P4** | Daily rate > 2× trailing mean | RB-12 — data steward |

### Alert hygiene

| Rule | Why |
|---|---|
| No alert without a runbook | An unactionable page at 03:00 trains people to ignore pages |
| No alert on a symptom with a known benign cause | Noise destroys signal |
| P1 and P2 page; P3 and P4 raise a ticket | Not everything is an emergency |
| Every page reviewed weekly for value | Alerts that never led to action are removed |

---

## 8. Reporting cadence

| Report | Frequency | Audience | Produced from |
|---|---|---|---|
| Service health summary | Weekly | SRE, service owner | Dashboards |
| Spend and value | Monthly | Service owner, FinOps | Ledger |
| Model performance pack | Monthly | Model Risk | Evaluation harness |
| Security events and probe results | Monthly | Security, MLRO | `security_event`, adversarial suite |
| Control attestation (zero autonomous dispositions, zero invented citations) | Monthly | MLRO, Internal Audit | Control report |
| Data quality | Daily digest | Data steward | Quarantine queue |
| Deviation notifications | On occurrence, within 1 business day | Model Risk, service owner | Banding engine |

The control attestation is deliberately a standing monthly report rather than an
answer produced on request. A control nobody measures routinely is a control
nobody can evidence.

---

## 9. Operational control bands

Section 3 sets service-level objectives. This section adds the **automated
response** to a deviation, using the pattern in Anthropic's *AI-Native SDLC
Playbook* Maintain play: deterministic detection, with sigma-banded tiers
deciding what an agent may do about it.

| Property | Rule |
|---|---|
| Detection | Entirely deterministic — mean and standard deviation over a rolling window, with Western Electric rules so slow drift is caught as well as spikes. **No model is involved in detection.** |
| Configuration | Version-controlled `bands.yaml`, unit tested, reviewed like code |
| Invocation | A scheduled job or a webhook from the monitoring stack; the agent runs stateless and non-interactive |
| Output | A triaged finding in the programme's change flow, never a direct production action |

```yaml
# ops/bands.yaml
metric: post_deploy_5xx_rate
baseline: rolling_30d
rules: western_electric
tiers:
  1sigma: { action: log }
  2sigma: { action: diagnose, tools: "Read,Grep,Bash(gh run view *)" }
  3sigma: { action: propose, routes: [pull_request, runbook:rollback-deploy] }
```

### 9.1 Two gradients, deliberately

The autonomy gradient here **increases** with severity: log, then diagnose
read-only, then propose an action. That is right for an operational incident,
where a worsening situation is one you want more help with, faster.

It is the opposite of the model-quality gradient in AMLI-MRM-001 §6.1, where
autonomy **decreases** with severity: at band 3 automated change is halted
pending human triage. That is right for a model's own quality metrics, where a
large deviation is precisely when self-tuning should be trusted least.

| Metric class | Examples | Gradient | Specified in |
|---|---|---|---|
| **Operational** | post-deploy 5xx rate, batch failure rate, queue depth, ingestion lag, CI failure rate | Escalating autonomy | This section |
| **Model quality** | recall, accuracy, groundedness, override rate, drift | Decreasing autonomy | AMLI-MRM-001 §6.1 |

Applying the wrong gradient to the wrong metric class is a design error, not a
tuning choice. An agent that responds to falling recall by changing itself more
aggressively is the failure mode the model-risk framework exists to prevent.

### 9.2 Dismissals tune the bands

A finding the service owner dismisses is signal about the band, not noise to
ignore. Dismissal rate per metric is reviewed monthly, and a band producing
findings nobody acts on is widened or retired.
