# Requirements Traceability Matrix

| | |
|---|---|
| **Document ID** | AMLI-RTM-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Business Analyst |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

Every *Must* requirement traces forward to a component, an interface and a test,
and backward to a business driver. A requirement without a test is not ready to
build; a test without a requirement is scope creep.

---

## 1. Business requirement → functional requirement → design

| BR | Requirement (abbreviated) | FRs | Component | ADR | Test |
|---|---|---|---|---|---|
| BR-001 | Disposition with reasoning per alert | FR-001…012, FR-031…046 | Ingestion, Agent Runtime | ADR-003 | E2E-01, UNIT-parser |
| BR-002 | Claims cite evidence present in the record | FR-021…030, FR-048…050 | Evidence Collector, Groundedness Checker | ADR-004, ADR-011 | UNIT-grounding, E2E-02 |
| BR-003 | No autonomous closure, filing or amendment | FR-041, FR-052, FR-061…068, FR-071 | Scope registry, Decision service, DB trigger | ADR-005 | ARCH-scopes, DB-trigger, CTRL-01 |
| BR-004 | No customer-facing content | FR-090 | Egress guardrail | ADR-006 | ARCH-no-channel, ADV-tipping-off |
| BR-005 | Thresholds from a versioned catalogue, cited | FR-013…020 | Rule Resolver | ADR-007 | UNIT-rules, INT-catalogue |
| BR-006 | Evidence captured, hashed, retained | FR-021…030 | Evidence Collector, S3 | ADR-011 | INT-evidence, CTRL-02 |
| BR-007 | Human decision with actor recorded | FR-061…068 | Decision service | — | DB-trigger, E2E-03 |
| BR-008 | Consolidation proposed, history preserved | FR-054…060 | Case service | ADR-018 | INT-case, E2E-04 |
| BR-009 | Cost recorded per alert | FR-037, FR-086 | Ledger | — | INT-ledger, OBS-cost |
| BR-010 | Append-only audit, reconstructable | FR-004, FR-032, FR-042, FR-093 | Ledger, audit chain | ADR-008, ADR-017 | CTRL-03, E2E-05 |
| BR-011 | Payment reference text untrusted always | FR-010, FR-087, FR-089 | Ingestion, Envelope | ADR-006 | ADV-suite, UNIT-envelope |
| BR-012 | Jurisdictional segregation | FR-011, FR-091, FR-096 | RLS, projection | ADR-014 | SEC-rls, INT-tenancy |
| BR-013 | Continuous quality measurement, deviations raised | FR-077…086 | Evaluation Service | ADR-010 | EVAL-harness |
| BR-014 | Change requires evidence and approval | FR-080…084, FR-095 | Gate, release registry | ADR-009 | UNIT-gate, E2E-06 |
| BR-015 | Draft narratives, never submit | FR-069…072 | Report service | — | ARCH-no-submit |
| BR-016 | Degrade safely rather than answer ungrounded | FR-017, FR-043, FR-053, FR-076 | Runtime | ADR-003 | UNIT-safe-degrade, E2E-07 |
| BR-017 | Outcome, adjudication, label stored separately | FR-077, FR-078 | Labelling service, DB constraints | ADR-010 | UNIT-labelling, DB-check |
| BR-018 | Adversarial testing every release | FR-094 | Pipeline | — | ADV-suite (gate G5) |

---

## 2. Non-functional requirement → design → verification

| NFR | Target | Design element | Verified by |
|---|---|---|---|
| NFR-001…003 | Run latency p50/p95/p99 | Routing, bulkheads, Fargate scaling | Load test |
| NFR-005, 006 | Batch windows | Step Functions, SQS, autoscaling | Load test |
| NFR-011, 012 | Scale and headroom | Queue-depth autoscaling with ceiling | Load test |
| NFR-018…021 | Availability | Multi-AZ, blue/green | Chaos, synthetic monitoring |
| NFR-022…024 | RTO / RPO | PITR, cross-region copy, restartable batch | Quarterly restore rehearsal |
| NFR-026 | Provider failure survivable | Circuit breaker, fallback | Chaos (provider fault injection) |
| NFR-029…031 | Reconstructability | `ai_run` spine, prompt capture, evidence hashes | CTRL-03, UC-09 walkthrough |
| NFR-030 | Append-only audit | INSERT-only grant, hash chain | Daily verification job, SEC test |
| NFR-033 | Trace propagation | OpenTelemetry context | INT-tracing |
| NFR-035…038 | Encryption, identity, least privilege | TLS, CMK, workload identity, IAM matrix | IaC scan, pentest |
| NFR-039 | Ungrantable scopes | Start-up assertion | ARCH-scopes |
| NFR-040 | Injection resistance | Four-layer defence | Adversarial suite, gate G5 |
| NFR-045…051 | Privacy | Region pinning, field projection, masking | DPO review, PII scan |
| NFR-052…054 | Recall, accuracy, groundedness | Evaluation harness, evidence gate | EVAL-harness |
| NFR-058 | Repeat agreement | Pinned versions, 3-repeat measurement | EVAL-harness |
| NFR-059…063 | Cost | Ledger, routing, spend cap | FinOps dashboard, budget test |
| NFR-064 | Coverage | — | Coverage gate in CI |
| NFR-066, 067 | Zero-downtime deploy, 15-min rollback | Blue/green, forward-only migrations | Release rehearsal |
| NFR-073, 074 | Accessibility | Workspace build standards | Automated + manual audit |
| NFR-076, 077 | Replaceability | Ports and adapters | Contract test suite |

---

## 3. Use case → requirements → tests

| UC | Requirements | Tests |
|---|---|---|
| UC-01 Triage an alert | FR-031…053 | E2E-01, UNIT-pipeline |
| UC-02 Review and decide | FR-061…068 | E2E-03, UI-acceptance |
| UC-03 Consolidate | FR-054…060 | E2E-04 |
| UC-04 Draft narrative | FR-069…072 | E2E-08 |
| UC-05 Override with reason | FR-064, FR-079 | E2E-03b, UNIT-mining |
| UC-06 Validate performance | FR-077…078, FR-085 | EVAL-harness |
| UC-07 Propose and approve change | FR-079…084 | E2E-06, UNIT-gate |
| UC-08 Operate the service | FR-098…100 | Runbook rehearsal |
| UC-09 Reconstruct an investigation | FR-020, FR-042 | CTRL-03 |
| UC-10 Ungrounded or unparseable | FR-045, FR-049…053 | UNIT-safe-degrade, E2E-07 |
| UC-11 Withstand injection | FR-010, FR-087…090 | ADV-suite |
| UC-12 Ingest and quarantine | FR-001…012 | INT-ingestion, contract suite |
| UC-13 Write back | FR-073…076 | INT-writeback, contract suite |
| UC-14 Data subject request | NFR-051 | Procedure walkthrough |

---

## 4. Control attestation map

The controls an auditor or supervisor will ask to see evidenced, and where the
evidence lives.

| Control | Claim | Evidence | Frequency |
|---|---|---|---|
| CTRL-01 | No disposition without a human decision | `amli_dispositions_without_human_decision = 0`; DB trigger; permission matrix | Monthly attestation |
| CTRL-02 | Evidence captured and unaltered | Hash verification sample; Object Lock configuration | Weekly sample, monthly report |
| CTRL-03 | Any investigation reconstructable | Reconstruction of a randomly chosen historic run within 1 hour | Quarterly exercise |
| CTRL-04 | No invented citations in production | `amli_invented_citation_total = 0` | Monthly attestation |
| CTRL-05 | The agent cannot file, close or write | Start-up assertion log; architecture test results; absence of capability in SBOM-scanned code | Per release |
| CTRL-06 | No customer-facing content emitted | Egress guardrail results; absence of any customer channel adapter | Per release + monthly |
| CTRL-07 | Thresholds match the configured source | Catalogue diff against source document | Per rebuild, quarterly verification |
| CTRL-08 | Performance within floors | Evaluation pack with n, basis distribution, confidence intervals | Monthly to MRM |
| CTRL-09 | Adversarial resistance maintained | Suite results per release candidate | Per release |
| CTRL-10 | Jurisdiction isolation holds | RLS test results; access review | Per release + quarterly |

---

## 5. Coverage summary

| Category | Total | Traced to a component | Traced to a test | Gap |
|---|---|---|---|---|
| Business requirements | 18 | 18 | 18 | 0 |
| Functional (Must) | 86 | 86 | 86 | 0 |
| Functional (Should) | 15 | 15 | 13 | **2** |
| Non-functional | 79 | 79 | 76 | **3** |

### Open gaps

| Item | Gap | Resolution |
|---|---|---|
| FR-044 challenger model | No test defined | Phase 3 — test designed with the challenger capability |
| FR-101 model inventory export | No test defined | Phase 3 — format agreed with MRM first |
| NFR-049 no training on customer data | Contractual, not technically testable by us | Annual provider attestation, recorded as evidence |
| NFR-078 exit path per managed service | Analysis, not a test | Exit analysis document per service, Phase 1 |
| NFR-079 licence compliance | Automated scan, gate not yet wired | Phase 1 pipeline work |

These five are tracked in AMLI-RAID-001 as issues, not carried silently.
