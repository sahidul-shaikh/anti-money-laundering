# Business Requirements Document

| | |
|---|---|
| **Document ID** | AMLI-BRD-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Product Owner |
| **Approver** | Head of Financial Crime Technology |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Executive summary

Transaction monitoring is automated. Everything after it is not.

A detection engine raises an alert; a Level-1 analyst then opens the party
record, the KYC file, the transaction history and any prior alerts, forms a
view, and writes it down. The decision itself is usually obvious by the time the
evidence has been gathered — the work is the gathering. The institution prices
that work at **GBP 17.00 per alert**, and the queue moves only as fast as the
people on it.

The AML Alert Investigator assembles the evidence and proposes a disposition
with citations, so that an analyst reviews a recommendation instead of starting
from nothing. It never files, never closes an alert on its own, and never writes
to a customer.

The target is **GBP 12.00 per alert** at no loss of detection: a recall floor of
90% on alerts that should escalate, which is the binding constraint and the only
one a regulator will ask about.

---

## 2. Business context and drivers

### 2.1 The problem

| # | Driver | Evidence |
|---|---|---|
| D-1 | **Alert volume exceeds investigation capacity.** Detection thresholds are tuned to miss nothing, so they fire on salaries, trading rhythms, settlement proceeds and property deposits. | Industry false-positive rates for transaction monitoring are commonly quoted between 90% and 97%. The client extract supplied for this programme contains 35 alerts across 25 cases, every one of which escalated — see §7 for why that is a measurement problem, not a performance statistic. |
| D-2 | **Unit cost is fixed and labour-shaped.** Each alert consumes roughly 30 minutes of fully loaded L1 analyst time. | Client-supplied baseline: GBP 17.00 per alert. |
| D-3 | **The deadline is regulatory, not operational.** A SAR has a statutory filing window. A backlog is a compliance exposure, not an efficiency problem. | BSA filing deadlines; FCA SYSC 6 expectations on timeliness. |
| D-4 | **Output is inconsistent between analysts.** Two investigators, the same alert, different days, materially different narratives. | Raised repeatedly in internal QA sampling; also a standing model-risk and audit finding across the industry. |
| D-5 | **Tuning thresholds down is not an available lever.** Raising a threshold reduces alerts by missing activity. | A supervisor will not accept a cheaper control that detects less. |
| D-6 | **Investigation knowledge is not retained.** When an experienced investigator leaves, the reasoning leaves with them. | No structured capture of *why* an alert was closed, only that it was. |

### 2.2 Why an AI agent, and why now

The task is evidence assembly and written reasoning over a bounded, structured
record with an explicit rule to apply. That is a good fit for a language model
*provided* three things are true, and the architecture in AMLI-HLD-001 exists to
make them true:

1. every claim is traceable to a transaction reference that exists in the data;
2. the agent recommends and a person decides;
3. the whole execution can be reconstructed afterwards.

### 2.3 Why this use case is harder than it looks

Stated plainly, because it shapes the non-functional requirements.

- **The cost of error is asymmetric in both directions.** A missed escalation is
  unreported laundering. A wrong escalation wastes an investigator's day. These
  cannot be traded one for one, which is why a single accuracy figure is not an
  acceptable success measure (see §5).
- **The agent reads attacker-controlled text.** Payment reference and remittance
  free text is written by whoever sent the payment and travels unmodified into
  the prompt. It is the one genuinely hostile input in the pipeline.
- **Tipping off is a criminal offence, not a policy breach.** Any customer-facing
  output path is a legal exposure and must be impossible by construction.

---

## 3. Scope

### 3.1 In scope

| # | Item |
|---|---|
| S-1 | Ingestion of alerts, parties, accounts and transactions from the Actimize estate (API where available, file extract otherwise) |
| S-2 | Retrieval of the applicable detection rule and thresholds, cited to source |
| S-3 | Evidence assembly, capture and immutable retention for each investigation |
| S-4 | Agent-produced findings with mandatory citation to captured evidence |
| S-5 | A recommended disposition per alert, with reasoning |
| S-6 | Alert-to-case consolidation proposals |
| S-7 | Human review workspace: accept, override, request more information |
| S-8 | Write-back of recommendation and evidence pack to the Actimize case record |
| S-9 | Narrative drafting support for reporting (draft only; never submission) |
| S-10 | Full execution telemetry, cost accounting and model-risk evidence |
| S-11 | Continuous evaluation, failure clustering and governed change proposals |
| S-12 | Adversarial testing of the agent on every release |

### 3.2 Out of scope

| # | Item | Rationale |
|---|---|---|
| X-1 | Alert generation and detection threshold tuning | Remains in Actimize SAM; we consume, we do not detect |
| X-2 | Replacing the case management system | ActOne remains the system of record for cases |
| X-3 | Filing to FinCEN or any FIU | The agent drafts; the MLRO files |
| X-4 | Sanctions, PEP and watchlist screening | Separate control, separate programme |
| X-5 | Any customer-facing communication | Prohibited by C-3 |
| X-6 | Autonomous closure of alerts | Prohibited by C-2 |
| X-7 | Fraud, market abuse and other financial-crime typologies | Candidate for a later release on the same asset |

### 3.3 Scenarios in scope for the first release

| Scenario | Description | Detection model |
|---|---|---|
| SAS10014 | Structured Withdrawals | AML-STR |
| SAS10056 | Structured Premiums | AML-STR |
| SAS10016 | Structured Deposits Across Locations | AML-STR |
| SAS10050 | Payments Made Using High-Risk Instruments | AML-ECT |
| SAS10602 | Multiple External Remitters, One Internal Beneficiary | AML-EBB |
| SAS10012 | Recurring Phone Number | AML-MLT |

> SAS10602 and SAS10012 require counterparty and party-relationship data that
> the current extract does not carry. They are scheduled in Phase 3 of
> AMLI-PLAN-001, gated on DEP-004.

---

## 4. Stakeholders

| Stakeholder | Interest | Involvement |
|---|---|---|
| Head of Financial Crime Technology | Accountable sponsor; approves the value contract and every production change | Approver |
| MLRO | Owns reporting decisions; must be satisfied the agent cannot file or tip off | Consulted, signs off C-2 and C-3 |
| L1 Investigations Manager | Owns throughput and quality of the alert queue | Primary business owner |
| L1 Analyst | Day-to-day user; reviews recommendations | Primary user; UAT |
| L2 Investigator | Handles escalated cases | Secondary user |
| Model Risk Management | Validates the model under SR 11-7 before production | Approver, independent |
| Data Protection Officer | Lawful basis, minimisation, retention, cross-border | Consulted |
| Information Security | Threat model, controls, penetration testing | Approver |
| Internal Audit | Reconstructability and control effectiveness | Consulted |
| Platform / SRE | Runs it | Responsible |
| Actimize vendor team | Interface contracts and supportability | Consulted |

---

## 5. Objectives and success criteria

### 5.1 The value contract

Agreed before build, measured after every run, and the basis on which any
proposed change is accepted or refused.

| Measure | Baseline | Target | Floor |
|---|---|---|---|
| Cost per alert handled | GBP 17.00 | **GBP 12.00** | must not exceed baseline |
| Escalation recall | — | ≥ 0.95 | **≥ 0.90 (binding)** |
| Overall accuracy | — | ≥ 0.90 | ≥ 0.85 |
| Groundedness of citations | — | 1.00 | **1.00 (no invented references)** |
| Reports the agent may file | 0 | 0 | **0 (absolute)** |
| Median analyst handling time | 30 min | ≤ 20 min | ≤ 30 min |

**Recall is the binding constraint.** The supervisor's question is never how much
was saved; it is what was missed. Any change that improves cost while reducing
recall below the floor is refused by the gate, regardless of its economics.

### 5.2 Business objectives

| # | Objective | Success criterion | Measured by |
|---|---|---|---|
| O-1 | Reduce the unit cost of alert handling | ≤ GBP 12.00 per alert, sustained over a full month | AMLI-OBS-001 VALUE layer |
| O-2 | Detect no less than today | Escalation recall ≥ 0.90 against adjudicated labels | AMLI-MRM-001 outcome analysis |
| O-3 | Make every recommendation defensible | 100% of findings cite captured evidence; zero invented references in production | AMLI-OBS-001 AGENT layer |
| O-4 | Make every investigation reconstructable | Any disposition in the last 7 years can be replayed with the prompt, model, policy and evidence of the day | AMLI-NFR-001 NFR-031 |
| O-5 | Shorten the queue | 95th-percentile alert age at disposition reduced by 50% | Operational MI |
| O-6 | Retain investigative reasoning | Structured findings captured on 100% of cases | Data completeness report |
| O-7 | Keep the control auditable and approvable | MRM validation passed; no high-severity audit findings at go-live | Validation report |

### 5.3 Explicit non-objectives

- Not headcount reduction. The design assumes the same investigators handling a
  larger queue with better evidence. Any headcount case is the client's to make
  and is not an input to this design.
- Not full automation. C-2 forbids it.
- Not improved detection. We do not change what SAM raises.

---

## 6. Business requirements

| ID | Requirement | Priority | Objective |
|---|---|---|---|
| BR-001 | The system shall produce, for each in-scope alert, a recommended disposition with supporting reasoning | M | O-1, O-3 |
| BR-002 | Every factual claim in a recommendation shall cite a transaction, party or account record that exists in the evidence captured for that investigation | M | O-3 |
| BR-003 | The system shall never close an alert, open or close a case, amend a party record, or submit a report without an authorised human decision | M | O-7 |
| BR-004 | The system shall never generate or emit customer-facing content | M | O-7 |
| BR-005 | Detection thresholds applied in reasoning shall be retrieved from a versioned rule catalogue traceable to the source specification, not transcribed into prompts | M | O-3, O-4 |
| BR-006 | The system shall capture, hash and retain the evidence available at investigation time, not a pointer to data that may later change | M | O-4 |
| BR-007 | The system shall record the human decision, the deciding actor, and whether the decision agreed with the recommendation | M | O-2, O-7 |
| BR-008 | The system shall propose consolidation of alerts that belong to one investigation, and preserve the link history | S | O-5 |
| BR-009 | The system shall record, per alert, the cost of producing the recommendation and the resulting handling cost | M | O-1 |
| BR-010 | The system shall maintain an append-only audit trail sufficient to reconstruct any disposition | M | O-4, O-7 |
| BR-011 | The system shall treat payment reference and remittance free text as untrusted data under all circumstances | M | O-7 |
| BR-012 | The system shall support jurisdictional segregation of data and policy | M | O-7 |
| BR-013 | The system shall measure its own quality continuously against adjudicated outcomes and raise deviations | M | O-2 |
| BR-014 | A change to any model, prompt, policy or threshold shall require evaluation evidence and documented approval before production | M | O-7 |
| BR-015 | The system shall draft, but never submit, regulatory report narratives | S | O-5 |
| BR-016 | The system shall degrade to a safe state — no recommendation — rather than produce an ungrounded one | M | O-3 |
| BR-017 | The system shall store outcome, adjudication and label confidence separately and shall not treat a filing as proof of suspicion | M | O-2 |
| BR-018 | The system shall be subject to adversarial testing before every production release | M | O-7 |

---

## 7. Label integrity — a stated business constraint

This is called out at business level because it determines whether any
performance figure quoted to a supervisor is defensible.

The supplied extract contains 35 alerts, all of which escalated to a case and
filed a report: 25 SARX, 9 CTR, 1 CTRX. A naive labelling of "filed = should
escalate" would score an agent that escalates everything at 100% recall.

Two things are wrong with that:

1. **A CTR is a threshold obligation.** Cash activity above a regulatory limit
   must be reported whether or not anything is suspicious. Nine of the 35 are
   therefore not evidence of suspicion at all.
2. **Closure is not proof of innocence either.** An alert closed by an analyst
   under time pressure is weak evidence that nothing was there.

**BR-017** therefore requires outcome, adjudication and label confidence to be
stored separately. Performance may only be quoted against adjudicated labels,
with the confidence basis stated. AMLI-MRM-001 §4 defines the adjudication
process and the minimum sample.

---

## 8. Constraints

| # | Constraint | Type | Source |
|---|---|---|---|
| C-1 | Every claim must cite evidence present in the captured record | Regulatory / quality | PRD §5.1 |
| C-2 | No autonomous closure or filing; a human decides | Regulatory | PRD §5.2, MLRO |
| C-3 | Tipping off must be impossible by construction, not discouraged by instruction | Legal — 31 U.S.C. 5318(g)(2) | PRD §5.3 |
| C-4 | Payment reference text is evidence to report, never instruction to follow | Security | PRD §5.4 |
| C-5 | Detection thresholds follow Actimize AML-SAM defaults; we do not invent our own | Regulatory | PRD §5.5 |
| C-6 | Every disposition must be reproducible from what was recorded | Audit | PRD §5.6 |
| C-7 | Customer data must not leave the approved jurisdiction or cloud region | Legal / DPO | Client policy |
| C-8 | Actimize SAM remains the authoritative alert and case system | Architectural | §3.2 X-2 |
| C-9 | Model inventory registration and MRM validation required before production | Governance | SR 11-7 |
| C-10 | No customer PII in telemetry, metrics or non-production environments | Privacy | DPO |

---

## 9. Assumptions

| ID | Assumption | Impact if false |
|---|---|---|
| ASM-001 | Actimize exposes alert, party, account and transaction data via API or a scheduled extract | Ingestion redesign; Phase 1 slips |
| ASM-002 | The client can provide, or fund the creation of, an adjudicated label set of at least 1,000 alerts | No defensible accuracy claim; O-2 unmeasurable |
| ASM-003 | Amazon Bedrock is approved for use with customer data in the client's region | LLM layer re-points to another provider; ADR-002 revisited |
| ASM-004 | Counterparty data is obtainable for Phase 3 scenarios | SAS10602 and SAS10012 drop from scope |
| ASM-005 | Investigators will accept a recommendation-first workflow | Adoption risk; handling-time objective at risk |
| ASM-006 | The Solution Guide may be used as the threshold source under the existing vendor agreement | Thresholds must be re-sourced from the deployed configuration |

Full RAID tracking is in AMLI-RAID-001.

---

## 10. Regulatory and policy context

| Instrument | Relevance |
|---|---|
| Bank Secrecy Act, 31 U.S.C. 5311 et seq. | SAR and CTR obligations |
| 31 U.S.C. 5318(g)(2) | Tipping-off prohibition — drives C-3 |
| 31 U.S.C. 5324 | Structuring as an offence — the typology the first release targets |
| 31 C.F.R. 1020.320 | SAR filing timelines |
| FFIEC BSA/AML Examination Manual | Supervisory expectations on monitoring and investigation quality |
| SR 11-7 / OCC 2011-12 | Model risk management — drives AMLI-MRM-001 |
| UK POCA 2002 s.330–333A | UK reporting and tipping-off equivalents, where the deployment is UK |
| JMLSG Guidance Part I | UK industry expectations |
| EU AMLD 5/6 and AMLR | Where an EU entity is in scope |
| GDPR / UK DPA 2018 | Lawful basis, minimisation, retention, automated-decision provisions |
| EU AI Act | Classification assessment required; an AML triage support tool is expected to fall below high-risk only because a human decides — C-2 is therefore also an AI Act control |

> **Automated decision-making.** Because C-2 guarantees a human decision on
> every disposition, the system is decision *support*. This position must be
> re-confirmed by Legal before each jurisdictional rollout and is tracked as
> DEP-007.

---

## 11. Acceptance of this document

| Role | Name | Date | Signature |
|---|---|---|---|
| Product Owner | | | |
| Head of Financial Crime Technology | | | |
| MLRO | | | |
| Model Risk Management | | | |
| Data Protection Officer | | | |
