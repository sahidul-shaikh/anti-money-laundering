# Glossary and abbreviations

| | |
|---|---|
| **Document ID** | AMLI-GLO-001 |
| **Version** | 0.1 |
| **Status** | Draft |
| **Owner** | Business Analyst |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Financial crime

| Term | Definition |
|---|---|
| **Alert** | The output of a detection scenario: a statement that a pattern crossed a threshold on an account or party in a given period. An alert is a *detection event*, not a finding and not an accusation. |
| **AML** | Anti-Money Laundering. |
| **BSA** | Bank Secrecy Act (US, 31 U.S.C. 5311 et seq.) — the statute requiring SAR and CTR filing. |
| **Case** | The investigation container. One case may group several alerts on the same party, account or typology. Opened by a person or by consolidation policy; closed by a decision. |
| **CDD / EDD** | Customer Due Diligence / Enhanced Due Diligence. |
| **CTR** | Currency Transaction Report. Filed when cash activity exceeds a regulatory threshold. **A CTR is a threshold obligation, not a suspicion finding** — see §4, label integrity. |
| **Disposition** | The conclusion reached on an alert or case: close with no further action, escalate to case, or request more information. |
| **False positive** | An alert that, on investigation, had an innocent explanation. The majority of transaction-monitoring alerts. |
| **FinCEN** | Financial Crimes Enforcement Network — the US financial intelligence unit that receives SARs. |
| **Integration (laundering stage)** | The final stage: criminal funds re-enter the legitimate economy with an apparently lawful origin. Not to be confused with systems integration. |
| **JMLSG** | Joint Money Laundering Steering Group — UK industry guidance. |
| **KYC** | Know Your Customer. The identity, occupation, income and expected-activity record held on a party. |
| **Layering** | The second stage of laundering: moving funds through transactions to obscure their origin. |
| **MLRO** | Money Laundering Reporting Officer. The accountable individual who decides whether a report is filed. |
| **Placement** | The first stage of laundering: introducing criminal proceeds into the financial system. |
| **SAR / STR** | Suspicious Activity Report (US) / Suspicious Transaction Report (elsewhere). Filed when suspicion is reached. |
| **Structuring** | Deliberately breaking a large amount into smaller transactions to stay below a reporting threshold. A federal offence in its own right under 31 U.S.C. 5324. |
| **Tipping off** | Disclosing to a customer, or to a third party, that a SAR has been or may be filed, or that an investigation is under way. **A criminal offence under 31 U.S.C. 5318(g)(2)**, and the equivalent provisions in UK POCA 2002 s.333A. |
| **Typology** | A recognised pattern of laundering behaviour (e.g. funnel accounts, trade-based laundering, smurfing). |

## 2. NICE Actimize estate

| Term | Definition |
|---|---|
| **Actimize** | NICE Actimize, the incumbent financial-crime platform assumed in this design. |
| **ActOne** | Actimize's case management and investigation workspace. |
| **AML-EBB** | Detection model: Burst in Beneficiary Activity. |
| **AML-ECT** | Detection model: Excessive Cash / Cash-Equivalent Transactions. |
| **AML-MLT** | Detection model: Customer Identity Discovery (multi-address, multi-ID, multi-name). |
| **AML-STR** | Detection model: Structuring Activity. |
| **Detection version** | The versioned configuration of a scenario — rule, thresholds, effective dates. Two alerts from the same scenario on different dates may have been raised by different detection versions, and an investigation must know which. |
| **SAM** | Suspicious Activity Monitoring — Actimize's detection engine. Remains the authoritative source of alerts in this design. |
| **Scenario** | A named, configured detection rule (e.g. `SAS10014` Structured Withdrawals). |
| **STAR / NarrateAI** | Actimize reporting and narrative generation components. |

> **Note on sourcing.** Entity and interface names attributed to Actimize in this
> design are derived from publicly available NICE Actimize product descriptions
> and from the threshold specifications in the client-supplied Solution Guide.
> They are a design proposal for integration, not a reproduction of Actimize's
> proprietary schema.

## 3. System and engineering

| Term | Definition |
|---|---|
| **Actor** | Any entity that can take an action of record — a named human user or an identified system principal. Every `DECISION` has an actor. |
| **AI_RUN** | The central integration record: one execution of the agent against one alert or case. Every model call, tool call, control check, evidence access and piece of feedback joins to it. See ADR-008. |
| **Control check** | A runtime security or policy evaluation performed during a run, with an outcome of allow, block or escalate. |
| **Disposition (system)** | One of `close_no_further_action`, `escalate_to_case`, `insufficient_information`. |
| **Evidence item** | An immutable record of what was available to the investigation at the time it was made: a source reference, capture timestamp, content hash and a protected snapshot. A live URL alone is not evidence. |
| **Finding** | An interpretation produced by the agent or an investigator, which cites evidence. A finding is not a decision. |
| **Groundedness** | The proportion of an answer's citations that resolve to references actually present in the source material. Computed deterministically, never judged by a second model. See ADR-004. |
| **Guardrail** | A deterministic control applied before, during or after a model call. |
| **Ledger** | The append-only record of every model call and every outcome, from which all cost, quality and telemetry figures are computed. Nothing is asserted twice. |
| **Prompt injection** | An attack in which instructions are smuggled into data the model reads — here, principally payment reference free text. |
| **Recall (escalation recall)** | Of the alerts that should have escalated, the proportion that did. The binding quality constraint. |
| **Trace ID** | A correlation identifier propagated across every service, log line and model call for one run. |
| **Untrusted-data envelope** | Explicit delimiting and labelling of attacker-controllable text so a model treats it as evidence to report, never as instruction to follow. See ADR-006. |
| **Value contract** | The agreed, measurable statement of what the product must achieve — baseline, target, quality floors, telemetry and approver — fixed before build and measured after every run. |

## 4. Labelling vocabulary

These four terms are deliberately distinct. Conflating them is the most common
source of invalid performance claims in alert-triage models, and the separation
is mandated by AMLI-DM-001 §6.

| Term | Meaning |
|---|---|
| **Outcome** | What the institution actually did. Factual and always known: alert closed, case opened, SAR filed, CTR filed. |
| **Adjudication** | What a qualified reviewer concluded the correct answer was, recorded separately from the outcome. |
| **Label** | The value used as ground truth when scoring the model. Derived from adjudication where available, never assumed from outcome alone. |
| **Label confidence** | How strongly the label is believed, and on what basis. A CTR filing is a weak basis for a suspicion label; a quality-assured adjudication is a strong one. |

## 5. Governance

| Term | Definition |
|---|---|
| **SR 11-7** | US Federal Reserve / OCC supervisory guidance on model risk management. The validation framework adopted in AMLI-MRM-001. |
| **Model inventory** | The institution's register of models in use, their owners, validation status and tier. |
| **Challenger model** | An alternative model run alongside the champion to test whether the champion remains the better choice. |
| **Four-eyes** | A control requiring two distinct authorised people for an action. |
| **RTO / RPO** | Recovery Time Objective / Recovery Point Objective. |
| **MoSCoW** | Must / Should / Could / Won't — requirement prioritisation. |
| **RAID** | Risks, Assumptions, Issues, Dependencies. |
