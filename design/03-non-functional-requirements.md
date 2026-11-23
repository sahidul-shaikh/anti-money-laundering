# Non-Functional Requirements

| | |
|---|---|
| **Document ID** | AMLI-NFR-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Solution Architect |
| **Approver** | Head of Financial Crime Technology |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Basis of sizing

All throughput and capacity figures derive from the reference institution
profile below. Where a client differs, the figures are recalculated and this
section is the only place that changes.

| Parameter | Value | Source |
|---|---|---|
| Monitored accounts | 4,000,000 | Client profile |
| Alerts raised per day (steady state) | 12,000 | Client profile |
| Peak day (month-end, post-tuning, backfill) | 40,000 | 3.3× steady state, observed |
| Alerts requiring full investigation | 100% | All alerts are triaged |
| Escalation rate (expected) | 6–9% | Historic |
| Transactions per alert (mean / p95) | 24 / 180 | Supplied extract, extrapolated |
| Investigators (L1 concurrent, peak) | 120 | Client profile |
| Retention period | 7 years | BSA / client policy |
| Jurisdictions at go-live | 1 (expanding to 4) | Programme scope |

---

## 2. Performance

| ID | Requirement | Target | Measurement |
|---|---|---|---|
| NFR-001 | Single-alert investigation latency, agent runtime, p50 | ≤ 12 s | `ai_run` duration, SYSTEM layer |
| NFR-002 | Single-alert investigation latency, p95 | ≤ 45 s | As above |
| NFR-003 | Single-alert investigation latency, p99 | ≤ 90 s | As above |
| NFR-004 | Interactive reviewer action (open case, view evidence) p95 | ≤ 1.5 s | API latency |
| NFR-005 | Daily batch completion for steady-state volume | 12,000 alerts within a 4-hour window | Batch run duration |
| NFR-006 | Peak-day batch completion | 40,000 alerts within a 10-hour window | Batch run duration |
| NFR-007 | Sustained agent throughput | ≥ 60 investigations per minute | Load test |
| NFR-008 | Ingestion lag from source availability to investigable state | ≤ 30 min, p95 | Ingestion telemetry |
| NFR-009 | Write-back delivery to ActOne | ≤ 5 min from decision, p95 | Integration telemetry |
| NFR-010 | Evidence retrieval for a reviewer | ≤ 2 s, p95, for objects within retention | Object store metrics |

> Latency targets are for the agent runtime only. They deliberately exclude
> provider queueing beyond our control, which is tracked separately as a
> supplier SLO in AMLI-OBS-001 §6.

## 3. Scalability and capacity

| ID | Requirement | Target |
|---|---|---|
| NFR-011 | Horizontal scaling of the agent runtime without code change | Linear to 10× steady state |
| NFR-012 | Headroom above peak at all times | ≥ 30% |
| NFR-013 | Concurrent reviewer sessions | ≥ 250 |
| NFR-014 | Database growth accommodated without redesign | 7 years at peak volume ≈ 30M alerts, 750M transactions, 110M runs |
| NFR-015 | Partitioning strategy supports pruning of expired partitions without downtime | Monthly partitions on time-series tables |
| NFR-016 | Multi-jurisdiction deployment without schema divergence | One schema, row-level scoping |
| NFR-017 | Degradation under overload is graceful: queue depth grows, latency rises, correctness does not change | Verified in soak test |

## 4. Availability and reliability

| ID | Requirement | Target |
|---|---|---|
| NFR-018 | Reviewer-facing service availability, business hours | 99.9% |
| NFR-019 | Reviewer-facing service availability, 24×7 | 99.5% |
| NFR-020 | Batch investigation service availability | 99.5% |
| NFR-021 | Planned maintenance window | Outside 06:00–20:00 local, with 5 business days' notice |
| NFR-022 | RTO — reviewer service | ≤ 4 hours |
| NFR-023 | RTO — batch investigation | ≤ 24 hours |
| NFR-024 | RPO — all persisted data | ≤ 15 minutes |
| NFR-025 | No single point of failure in any tier | Verified by failure injection |
| NFR-026 | Provider failure is survivable by fallback within the same run | ≤ 1 escalation, no human-visible failure |
| NFR-027 | In-flight work is not lost on instance termination | Verified by chaos test |
| NFR-028 | Poison messages are quarantined after a bounded number of attempts, never retried indefinitely | Max 5 attempts then dead-letter |

## 5. Auditability and reconstructability

| ID | Requirement | Target |
|---|---|---|
| NFR-029 | Every disposition traceable to the run, prompts, model version, rule version, policy version and evidence used | 100% |
| NFR-030 | Audit events are append-only and tamper-evident | Application role has no UPDATE or DELETE; hash chain verified daily |
| NFR-031 | Any investigation within the retention period can be reconstructed and re-rendered as it was | ≤ 1 hour to produce, for any record up to 7 years old |
| NFR-032 | Clock skew across services bounded | ≤ 100 ms, NTP-disciplined |
| NFR-033 | Trace identifier propagated across every service hop and model call | 100% of spans carry `trace_id` |
| NFR-034 | Record of who accessed what evidence, and why | 100% of accesses carry `access_purpose` |

## 6. Security

| ID | Requirement | Target |
|---|---|---|
| NFR-035 | Data encrypted in transit | TLS 1.3; TLS 1.2 minimum for legacy vendor endpoints, recorded as an exception |
| NFR-036 | Data encrypted at rest with customer-managed keys | AES-256, KMS CMK, annual rotation |
| NFR-037 | No long-lived static credentials | Workload identity only; no access keys in any environment |
| NFR-038 | Least privilege enforced per component | Documented IAM matrix, reviewed quarterly |
| NFR-039 | Destructive scopes unregisterable, not merely ungranted | Start-up assertion fails the service if present |
| NFR-040 | Prompt-injection resistance verified per release | Adversarial suite blocks a release on any new successful exploit |
| NFR-041 | Secrets never written to logs, prompts, telemetry or error messages | Automated scan in pipeline |
| NFR-042 | Penetration test before go-live and annually thereafter | Independent, with remediation to closure |
| NFR-043 | Vulnerability remediation SLAs | Critical 7 days, high 30 days, medium 90 days |
| NFR-044 | All dependencies scanned and attested; SBOM produced per release | SBOM published with each release artefact |

## 7. Privacy and data protection

| ID | Requirement | Target |
|---|---|---|
| NFR-045 | Customer data does not leave the approved region | Enforced by service control policy; verified by config scan |
| NFR-046 | Data minimisation — only the fields needed for investigation are supplied to the model | Field list reviewed and approved by the DPO |
| NFR-047 | No customer PII in telemetry, metrics, traces or non-production environments | Automated detection, zero tolerance |
| NFR-048 | Prompts and completions containing customer data are retained under the same controls as evidence | Same store, same retention, same access control |
| NFR-049 | No customer data used to train or fine-tune any model | Contractual with provider; verified in the model-use attestation |
| NFR-050 | Retention and deletion honoured, subject to legal hold | Automated expiry job with hold interlock |
| NFR-051 | Subject access and erasure requests supportable within statutory deadlines | Documented procedure; retrieval tested |

## 8. Model quality and risk

| ID | Requirement | Target |
|---|---|---|
| NFR-052 | Escalation recall against adjudicated labels | ≥ 0.90, binding |
| NFR-053 | Overall accuracy against adjudicated labels | ≥ 0.85 |
| NFR-054 | Groundedness — citations resolving to captured evidence | 1.00; any invented reference is a defect |
| NFR-055 | Confidence calibration — Brier score | ≤ 0.15, reviewed monthly |
| NFR-056 | Performance monitored continuously and reported monthly to MRM | Monthly pack produced automatically |
| NFR-057 | Any metric breaching its floor raises a deviation within one business day | Automated banding, see AMLI-MRM-001 §6 |
| NFR-058 | Reproducibility — the same inputs and the same release produce the same disposition | ≥ 95% agreement across three runs; variance quantified and published |

> Determinism note: language-model inference is not bit-reproducible. NFR-058
> therefore specifies *agreement*, and AMLI-MRM-001 §7 requires the residual
> variance to be measured and declared rather than assumed away.

## 9. Cost

| ID | Requirement | Target |
|---|---|---|
| NFR-059 | Inference cost per alert | ≤ GBP 0.08 |
| NFR-060 | Total technology cost per alert (compute, storage, inference, licence) | ≤ GBP 1.20 |
| NFR-061 | Fully loaded cost per alert handled, including human review | ≤ GBP 12.00 |
| NFR-062 | Cost attributable per alert, per case and per release | 100% of spend attributable |
| NFR-063 | Spend cap enforced per run and per period | Breach stops work and alerts, never silently continues |

## 10. Maintainability and operability

| ID | Requirement | Target |
|---|---|---|
| NFR-064 | Unit and integration test coverage of core domain logic | ≥ 85% line, ≥ 90% branch on the agent and evidence modules |
| NFR-065 | Mean time to restore from a known failure mode | ≤ 30 min with a documented runbook |
| NFR-066 | Deployment is zero-downtime for the reviewer service | Blue/green or rolling with health gates |
| NFR-067 | Rollback to the previous release | ≤ 15 min, exercised each release |
| NFR-068 | Infrastructure defined as code; no manual production change | 100%, enforced by drift detection |
| NFR-069 | Configuration change requires approval and produces a release | No runtime toggles for model, prompt, policy or threshold |
| NFR-070 | Every alert raised to on-call has a runbook entry | 100% |

## 11. Usability and accessibility

| ID | Requirement | Target |
|---|---|---|
| NFR-071 | Reviewer can reach the evidence behind any claim in one interaction | Single click or keystroke |
| NFR-072 | The recommendation is never presented without its evidence | Enforced in the component, not by convention |
| NFR-073 | Accessibility | WCAG 2.2 AA |
| NFR-074 | Keyboard-only operation of the review workflow | Full task completion without a pointing device |
| NFR-075 | Median analyst handling time per alert | ≤ 20 minutes |

## 12. Portability and compliance

| ID | Requirement | Target |
|---|---|---|
| NFR-076 | The LLM provider is replaceable behind the gateway abstraction | A second provider demonstrated in a spike before go-live |
| NFR-077 | The detection source is replaceable behind the ingestion adapter | Contract tests pass against a second source implementation |
| NFR-078 | No dependency on a proprietary service without a documented exit path | Exit analysis per managed service |
| NFR-079 | Licence compliance of all third-party components | Automated scan; no copyleft in distributed components |

---

## 13. Conflicts and resolutions

Non-functional requirements compete. Where they do, the resolution is recorded
here rather than left to implementation.

| Conflict | Resolution | Rationale |
|---|---|---|
| NFR-001 latency vs NFR-052 recall | Recall wins. Escalating a run to a stronger model is permitted even when it breaches the p50 latency target | A slow correct answer is acceptable; a fast missed escalation is not |
| NFR-059 inference cost vs NFR-054 groundedness | Groundedness wins, bounded by NFR-063 | The evidence gate exists precisely to spend more when the cheap answer cannot be trusted |
| NFR-029 reconstructability vs NFR-046 minimisation | Both hold: minimise what is *sent to the model*, retain in full what *was* sent | Minimisation governs disclosure, not record-keeping |
| NFR-058 reproducibility vs provider model updates | Pin model versions; a provider version change is a release | An unannounced model change would otherwise silently invalidate validation |
| NFR-011 scaling vs NFR-063 spend cap | Spend cap is absolute; scaling stops at the cap and queues | Unbounded autoscaling on a per-token cost is an incident, not a feature |
