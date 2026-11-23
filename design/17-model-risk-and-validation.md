# Model Risk and Validation Plan

| | |
|---|---|
| **Document ID** | AMLI-MRM-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Model Risk Lead |
| **Approver** | Head of Model Risk Management (independent) |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

Aligned to SR 11-7 / OCC 2011-12: conceptual soundness, outcomes analysis and
ongoing monitoring, with independent validation before production use.

---

## 1. Model definition and boundary

**What is the model?** Not just the language model. The regulated model is the
**decision-support system**: the rendered context, the retrieved rule, the
routing policy, the guardrail policy, the language model with its pinned
version, the verdict parser and the groundedness checker — taken together,
producing a recommended disposition.

That boundary is deliberate. A change to the prompt changes the model as much as
a change to the weights, which is why ADR-009 makes every one of these a
versioned asset and why `ai_run.agent_config_hash` records exactly which
combination produced a given recommendation.

### Model inventory entry

| Field | Value |
|---|---|
| Model name | AML Alert Investigator |
| Model ID | To be assigned by MRM on registration |
| Type | Generative AI decision-support, rule-assisted classification |
| Purpose | Recommend a disposition for a transaction-monitoring alert, with cited evidence |
| **Decision authority** | **None. Output is advisory; a human decides every disposition (C-2)** |
| Materiality tier | Expected **Tier 2** — material but not autonomous. Confirmed by MRM at registration |
| Owner | Head of Financial Crime Technology |
| Developer | AI Engineering, Financial Crime |
| Validator | Model Risk Management (independent) |
| Downstream dependency | Actimize SAM detection output, Actimize ActOne case record |
| Key limitation | Operates only on the six in-scope scenarios; produces no detection |

---

## 2. Conceptual soundness

| Question | Position | Evidence |
|---|---|---|
| Is the task appropriate for the technique? | Yes. It is evidence assembly and written reasoning over a bounded structured record with an explicit rule. It is not pattern discovery, and it does not replace detection | AMLI-BRD-001 §2.2 |
| Are the thresholds the model applies sound? | They are not the model's. They are the institution's configured Actimize thresholds, retrieved from a versioned catalogue with source and page | ADR-007, FR-013 |
| How is hallucination controlled? | Structurally. Every claim must cite a reference resolvable in captured evidence; unresolvable citations prevent the finding supporting a disposition and trigger escalation | ADR-003, ADR-004, FR-049 |
| What stops the model acting? | No capability exists. Destructive scopes are unregisterable, and a disposition decision requires a human actor enforced at the database | ADR-005, DB trigger |
| Is the output explainable? | Yes, at the level that matters: the reasoning, the specific transactions relied on, the rule applied and its source. Not at the level of model internals, and we do not claim otherwise | §8 limitations |
| Is it reproducible? | Not bit-exact — inference is non-deterministic. Agreement across repeats is measured and declared | NFR-058, §7 |

---

## 3. Data

| Aspect | Position |
|---|---|
| Input data | Alerts, parties, accounts and transactions sourced from the institution's own systems; no third-party or purchased data |
| Data quality controls | Schema and referential validation at ingestion; quarantine with reason codes; daily data-quality report |
| Representativeness | The evaluation set must cover all six in-scope scenarios, both dispositions, and the full range of party types and transaction volumes. Coverage is reported per evaluation |
| Known gaps | Counterparty and party-relationship data absent; two scenarios deferred to Phase 3 (DEP-004) |
| Synthetic data | Permitted in the evaluation set, labelled `synthetic`, reported separately, and **never mixed into a claim about production performance** |
| Sensitive attributes | Occupation, income, nationality and age are present and material to triage. Fairness testing in §6.4 is therefore mandatory, not optional |

---

## 4. Label integrity — the foundation of every metric

This section governs all performance reporting. It implements ADR-010.

### 4.1 The problem

In the supplied extract, all 35 alerts escalated and filed: 25 SARX, 9 CTR, 1
CTRX. Labelling "filed = should escalate" would score an escalate-everything
agent at 100% recall, and 10 of the 35 are currency-threshold reports that carry
no finding of suspicion at all.

### 4.2 The rule

**No metric may be computed against an outcome-inferred label.** Labels come
from adjudication, carry a basis and a confidence, and are enforced by database
constraint (`alert_label_complete`, `alert_ctr_never_labels`).

### 4.3 The adjudication exercise

A Phase 1 deliverable and a precondition of any accuracy claim.

| Parameter | Value |
|---|---|
| Minimum set | 1,000 alerts |
| Stratification | By scenario, by outcome, by party type, by transaction volume band |
| Adjudicators | Two experienced investigators, independently, blind to the outcome and to any agent output |
| Disagreement | Resolved by a third senior adjudicator; recorded as `adjudicated_dual` with the disagreement rate reported |
| Inter-rater agreement | Cohen's κ reported. **κ below 0.6 invalidates the exercise** and is itself a finding about investigation consistency |
| Refresh | 250 newly adjudicated alerts per quarter, to track drift and prevent over-fitting to a fixed set |
| Immutability | Frozen as an `evaluation_dataset_version`; a changed label creates a new version |

### 4.4 Reporting rule

Every published metric states: `n`, the `label_basis` distribution, mean
`label_confidence`, and the confidence interval. A metric without these is
rejected by the reporting pipeline.

---

## 5. Performance metrics and thresholds

| Metric | Definition | Target | **Floor** | Action on breach |
|---|---|---|---|---|
| Escalation recall | TP / (TP + FN) on adjudicated labels | ≥ 0.95 | **≥ 0.90** | Immediate deviation; candidate rollback |
| Accuracy | (TP + TN) / n | ≥ 0.90 | ≥ 0.85 | Deviation |
| Precision | TP / (TP + FP) | ≥ 0.60 | ≥ 0.45 | Monitor — low precision costs money, not detection |
| Groundedness | Resolved citations / total citations | 1.00 | **1.00** | **Any invented reference is a defect, raised as a bug** |
| Invented citation rate | Recommendations with ≥ 1 unresolved citation | 0 | 0 | P2 defect |
| Insufficient-information rate | Share of runs ending undecided | ≤ 0.05 | ≤ 0.12 | Investigate — rising values indicate degradation |
| Human override rate | Decisions disagreeing with the recommendation | ≤ 0.15 | ≤ 0.30 | The most important production signal; see §6.2 |
| Calibration (Brier) | On self-reported confidence | ≤ 0.15 | ≤ 0.25 | Recalibrate or stop surfacing confidence |
| Repeat agreement | Identical disposition across 3 runs | ≥ 0.95 | ≥ 0.90 | Investigate non-determinism |

**Recall is the binding constraint.** A change improving cost or precision while
taking recall below 0.90 is refused by the gate whatever its economics (FR-082).

---

## 6. Ongoing monitoring

### 6.1 Deviation banding

Deviations are expressed in standard errors of the measurement itself, so that
"two sigma" means something specific about this sample at this size rather than
being a label someone chose.

| Band | Deviation | Permitted response |
|---|---|---|
| 1 | < 1σ from target | Monitor. No action |
| 2 | 1σ – 2σ | Investigate; failure mining; a proposal may be raised |
| 3 | > 2σ, or any floor breach | Escalate to the model owner and MRM within one business day; candidate rollback; production use may be suspended |

### 6.2 The override signal

Human overrides are the only continuous, unbiased quality signal from
production — they do not require an adjudication exercise, and they arrive
daily. They are monitored by rate, by structured reason code, by scenario and by
reviewer, and they are the primary input to failure mining.

A rising override rate concentrated in one reason code is a model finding. A
rising rate concentrated in one reviewer is a training or consistency finding,
and is referred to the Investigations Manager rather than treated as model drift.

### 6.3 Drift

| Drift type | Monitored by | Threshold |
|---|---|---|
| Input distribution | PSI on scenario mix, transaction count, amount bands, party type | PSI > 0.2 raises a deviation |
| Output distribution | Disposition mix, week over week | > 3σ shift |
| Rule catalogue | Diff on every rebuild | Any change triggers re-evaluation |
| Provider model | Pinned identifiers; provider change notice | Any change is a release with full re-evaluation |

### 6.4 Fairness

Occupation, income, nationality and age are rendered to the model because they
are material to triage — a declared military salary is what explains a monthly
credit pattern. Because they are present, differential behaviour must be tested.

| Test | Method | Threshold |
|---|---|---|
| Disposition rate by protected characteristic proxy | Compare escalation rates across nationality, age band and occupation group, conditioned on scenario and amount band | Difference > 10 percentage points unexplained by the conditioning variables raises a finding |
| Counterfactual probe | Re-run a sample with the protected attribute altered and nothing else | A disposition flip is a finding, not noise |
| Narrative language audit | Sample of reasoning text reviewed for prejudicial framing | Qualitative, quarterly |

A finding here is reported to MRM and to Compliance. It is not treated as a
tuning parameter.

---

## 7. Non-determinism

Language-model inference is not reproducible bit for bit. Rather than claim
otherwise, the residual variance is measured and declared.

| Control | Detail |
|---|---|
| Temperature | Pinned low; the value is part of the versioned asset |
| Model version | Pinned; a provider update is a release |
| Prompt | Hashed per call; identical input produces identical prompt |
| Measurement | Every evaluation runs three repeats; repeat agreement is reported alongside accuracy |
| Disclosure | Published metrics carry the repeat-agreement figure, so a reader can distinguish model change from run variance |

---

## 8. Known limitations — stated, not buried

| # | Limitation | Consequence |
|---|---|---|
| L-1 | Groundedness verifies that a cited reference exists, not that the inference from it is sound | A plausible but wrong inference over real transactions passes the check. Human review and outcome analysis are the mitigations |
| L-2 | No counterparty or relationship data in Phase 1–2 | Two in-scope scenarios cannot be reasoned about and are deferred |
| L-3 | Explainability is at the level of reasoning and citations, not model internals | We do not claim mechanistic interpretability |
| L-4 | Performance depends on an adjudicated sample that is small relative to production volume | Confidence intervals are reported; claims are bounded accordingly |
| L-5 | The model does not detect; it triages what SAM raises | A typology SAM does not detect is invisible to this control |
| L-6 | Self-reported confidence is monitored but not used for routing | It is not trusted enough to act on |
| L-7 | Synthetic evaluation items do not evidence production performance | Reported separately, always |

---

## 9. Validation plan

| Stage | Activity | Owner | Exit criterion |
|---|---|---|---|
| V-1 | Conceptual soundness review | Independent validator | Documented opinion on §2 |
| V-2 | Data and label integrity review | Independent validator | Adjudication exercise accepted; κ ≥ 0.6 |
| V-3 | Outcome analysis on the adjudicated set | Validator with engineering support | All floors met with stated confidence intervals |
| V-4 | Benchmarking against the current manual process | Validator | Recall not materially below the human baseline |
| V-5 | Challenger comparison | Engineering, reviewed by validator | Champion justified, or replaced |
| V-6 | Stability and non-determinism assessment | Validator | Repeat agreement ≥ 0.90 |
| V-7 | Fairness assessment | Validator with Compliance | No unexplained differential above threshold |
| V-8 | Control testing — can the agent act? | Validator with Security | Attempts to close, file and write all fail; evidenced |
| V-9 | Adversarial assessment | Security, reviewed by validator | No successful exploit in the enveloped arm |
| V-10 | Ongoing monitoring design review | Validator | Metrics, bands and escalation accepted |
| V-11 | Validation report and model approval | Head of MRM | Signed; conditions recorded |

**Production use is not permitted before V-11.** A conditional approval must
state its conditions and their review date.

---

## 10. Change management

| Change | Re-validation required |
|---|---|
| Prompt text | Full re-evaluation; validator notified; approval by Compliance Admin and model owner |
| Routing policy | Full re-evaluation; **validator approval required** |
| Guardrail policy | Security review plus adversarial suite |
| Rule catalogue version | Re-evaluation on affected scenarios |
| Provider model version | **Full re-validation** — treated as a new model version |
| New scenario in scope | Full validation for that scenario, including its own adjudicated sample |
| Threshold override | Compliance approval; re-evaluation on the affected scenario |

Every change is recorded as a `change_approval` linking the evaluation run, the
candidate release and the approver (FR-083).

---

## 11. Decommissioning

| Trigger | Action |
|---|---|
| Recall below floor for two consecutive monitoring periods | Suspend production use; revert to manual triage; root cause before resumption |
| Unmitigated successful adversarial exploit | Immediate suspension |
| Provider withdrawal of a pinned model | Fall back to the alternative tier; re-validate before resuming normal routing |
| Business decision to retire | Evidence and audit retained for the full retention period regardless of decommissioning |

Reversion to manual triage must remain possible at all times. The queue, the
alerts and the evidence are all present in the institution's own systems; no
part of this design makes the manual process unavailable.
