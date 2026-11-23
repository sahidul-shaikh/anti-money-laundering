# AML Alert Triage Agent — Model Risk Management Documentation (SR 11-7)

**Model name:** AML Alert Triage Agent
**Model function:** Generates a structured `AlertTriageResponse` (disposition, typology assessment, confidence, rationale, evidence citations, data gaps) for retail/commercial AML alerts, for review by a human analyst.
**Document scope:** Covers the C-4 generation stage, C-5/C-6 groundedness verification, and the E-1 evaluation harness as specified by prior stages. Where prior-stage artifacts were delivered incomplete (see Open Items), this document states the gap rather than assuming a resolution.
**Model tier:** Tier 1 (output can trigger a Bank Secrecy Act/SAR filing decision pathway; errors carry regulatory and consumer-harm risk).

---

## INTENDED USE

The model is an **advisory triage aid**, not a decisioning system. It reads a single alert's context (`TaggedAlertContext`: transaction history capped at ≤500 rows, KYC attributes, screening scores, prior-SAR boolean, free-text memo/counterparty fields) and produces one of four dispositions — `CLOSE_NO_ACTION`, `ESCALATE_ANALYST_REVIEW`, `ESCALATE_SAR_RECOMMEND`, `ESCALATE_INSUFFICIENT_DATA` — plus a typology assessment, confidence score, rationale, and evidence citations.

**Permitted use:**
- Pre-screening and prioritization of alerts in the analyst queue.
- Surfacing a candidate disposition and typology with cited evidence for analyst confirmation or override.
- Flagging missing data (`ESCALATE_INSUFFICIENT_DATA`) to route an alert to manual handling rather than silently closing it.

**Explicitly not permitted (no model in this family may do this without separate model risk review and a new approval):**
- Auto-closing an alert without analyst sign-off.
- Filing, drafting, or transmitting a SAR.
- Taking any customer-facing action (contact, account freeze, transaction block).
- Serving as the sole basis for a disposition in the case file — every output must have a human-attributable decision of record.

**Users:** AML analysts and their line management, via the case management review queue only. The model's output is not authorized for export to any system or audience outside that queue (per T-4 of the security review, §2.3 boundary); doing so would require a separate confidentiality and tipping-off (31 U.S.C. §5318(g)(2)) risk assessment.

**Approved operating envelope:** Retail and commercial wire/ACH/SWIFT alerts surfaced by the existing TMS typology engine, in English-language free text, for accounts with a surrogate `account_id` (no raw PAN/SSN/DOB in context). Alerts outside this envelope (e.g., a new product line, a new typology taxonomy version, a non-English memo corpus) are out of scope until revalidated against GOLD-600/GOLD-150 (below).

---

## DATA LINEAGE

| Input | Source system | Trust classification | Notes |
|---|---|---|---|
| Transaction history (≤500 rows) | Core ledger / TMS | `system:core` | Row-selection algorithm for the 500-row cap is **not yet documented** (code review finding #5) — until specified and tested, any disposition on a truncated history carries unquantified risk of a hidden structuring pattern falling outside the retained window. |
| KYC attributes, screening scores | KYC/AFC systems | `system:core` | Retrieved facts; not content-adversarial. |
| `prior_sar_on_file` | Case management system | `system:core` | Boolean only; no SAR narrative ever enters context (data minimization at source). |
| Memo/remittance text, `counterparty_name` | Wire/ACH/SWIFT originator | `user_free_text:*` / adversary-influenced structured field | Attacker-controlled (T-1, T-2 of security review); capped at 140 cumulative characters of verbatim reproduction in `rationale`. |
| `account_id` | Surrogate key issued by core banking | `system:core` | No raw account/routing number, government ID, or full address enters context. |

Golden evaluation data (`GOLD-600`, `GOLD-150`) is drawn from closed cases with disposition known from SAR filings or documented analyst closure, refreshed quarterly to limit memorization. No training occurs on production alert data in this release — the model is used zero-shot/few-shot against a fixed prompt version; if fine-tuning is introduced in a future version, this document must be reissued with a training-data lineage section and a separate approval.

---

## PERFORMANCE MEASUREMENT

Performance is measured by the E-1 harness, gating every `(prompt_version, model_id, context_schema_version)` combination before production promotion. **Decoding parameters (temperature, top_p, seed) are not currently part of the run-identity triple** (code review finding #6) — until added, a "passing" eval result does not guarantee the same configuration is deterministic in production, and this is logged as an open item below, not treated as resolved.

Core metrics required at sign-off:
- **Disposition accuracy** (4-way, exact match) on `GOLD-600`: blocking threshold ≥ 0.92, warning band 0.90–0.92.
- **Macro-F1** on disposition, to prevent the majority class (`CLOSE_NO_ACTION`) from masking escalation errors.
- **Recall on `ESCALATE_SAR_RECOMMEND` specifically**, measured independently on both `GOLD-600` and the sequestered `GOLD-150`, with its own blocking threshold tighter than the all-class average. This is the single most important number in this document: `ESCALATE_SAR_RECOMMEND` is ~3% of base rate and a missed instance is a regulatory filing failure, not a cosmetic error. **As of this writing no numeric threshold has been set** — the E-1 pass-threshold table was delivered truncated after the first row (code review finding #1, #4). The model must not be promoted to production until this threshold exists, is reviewed, and is met.
- **Groundedness**: citation resolution rate, claim coverage, and fabrication rate (weighted more heavily than ordinary resolution misses) against `GOLD-600`, with a 10% human-audit sample per release.
- **Robustness (ASR)**: attack success rate on the adversarial suite (`ADV-SET`, ≥30 cases per attack class) — fraction of injection attempts that measurably change disposition/typology or leak injected text into `rationale` beyond the 140-character cap. No numeric blocking threshold has been confirmed (same truncation gap as above).
- **Schema-validity rate** on malformed/truncated/missing-field inputs.
- **Cost and latency**: p50/p95 latency and cost per 1,000 alerts, broken out by disposition, from the monthly-resampled `COST-SAMPLE`.

**Known measurement gaps to close before go-live sign-off:**
1. Full blocking/warning thresholds for groundedness, ASR, and cost (truncated in source document).
2. Test-retest consistency metric (N=5 reruns per `GOLD-150` alert, minimum agreement rate — not yet set).
3. Confirmation of whether generation is schema-enforced at decode time (constrained decoding) or free-form-then-parsed; this materially changes the expected schema-validity failure rate.

---

## LIMITATIONS

1. **Prompt-injection resistance is incomplete.** The 140-character quoting cap on `user_free_text:*` content in `rationale` is, per the security and code reviews, a prompt-level instruction with no confirmed post-generation programmatic enforcement. Until the cap is enforced in the parsing pipeline (not just requested of the model), the model must be treated as capable of leaking or being influenced by adversarial memo text beyond design intent.
2. **Structured-field manipulation is unmitigated.** `counterparty_name` and `counterparty_country` are adversary-influenceable but are tagged as trusted (`system:core`) facts, not flagged as interpretively untrusted. The model's typology judgment can be biased by a deliberately chosen counterparty name (e.g., "US Treasury Refund Dept") with no current control (T-2).
3. **Transaction-history truncation can hide the pattern it needs to see.** The row-selection rule for the ≤500-row cap is undocumented; structuring patterns built from many small transactions may fall outside the retained window under a naive recency- or amount-based selection.
4. **No determinism guarantee.** Decoding parameters are not fixed/documented as part of production configuration, and no consistency test exists; the same alert re-run may yield a different disposition.
5. **Fabrication detection is post-hoc, not preventive.** Evidence citations are checked for groundedness after generation; there is no constrained-decoding or allowlist-only citation mechanism at generation time. A fabricated citation can reach the analyst queue before the groundedness check runs.
6. **Undefined behavior on schema validation failure.** No documented deterministic fallback (retry policy, forced `ESCALATE_ANALYST_REVIEW`, alerting) exists for malformed JSON, invalid enum values, or missing mandatory fields at generation time.
7. **English-only, retail/commercial wire-pattern scope.** Not validated for other languages, products, or typology taxonomies.
8. **Confidence is not a calibrated probability** of correctness beyond what Brier score/ECE on `GOLD-600` demonstrates at each release; it must not be presented to analysts or examiners as a calibrated likelihood without that evidence attached to the release record.
9. **Not a SAR-filing system.** The model has no authority and must never be configured with authority to file, suppress, or imply the existence of a SAR outside the `prior_sar_on_file` boolean already present in its input.

---

## MONITORING

**Pre-production gate (every release):** All E-1 eval families (correctness, groundedness, robustness, cost) must pass blocking thresholds on `GOLD-600`, with a final sign-off run against the sequestered `GOLD-150` that no prompt-iteration cycle has seen. Sign-off is per `(prompt_version, model_id, context_schema_version)` triple; no partial reuse of a prior triple's pass result across a changed component.

**Production, 100% coverage, per-response:**
- Automated groundedness/citation-verification (C-5/C-6) runs on every output. A fabrication event or a citation that fails resolution is logged; a defect meeting the Severity-1 criteria (fabricated or wrong-account transaction ID) triggers the kill-switch path (see WITHDRAWAL) within 1 hour of detection.
- Automated schema-conformance check on every output; any non-conformant output routes to `ESCALATE_ANALYST_REVIEW` with `data_gaps` populated (pending final confirmation of this fallback rule per code review finding #2/#7) rather than being silently discarded or shown unparsed.
- Injection-leakage check: confirm no `user_free_text:*` content exceeds the 140-character cumulative cap and no injected imperative text appears as a stated finding.

**Production, sampled/periodic:**
- Monthly resample of `COST-SAMPLE` (500 alerts) to track cost and latency drift against live traffic shape.
- Quarterly refresh of `GOLD-600`/`GOLD-150` to detect memorization and dataset staleness; disposition accuracy and SAR-recall are re-measured against the refreshed set.
- 10% human audit of groundedness claim-coverage per release, to catch paraphrased or extractor-missed factual claims.
- Ongoing tracking of `ESCALATE_SAR_RECOMMEND` recall and the full confusion matrix (not just aggregate accuracy/F1) on a rolling basis, specifically to detect quiet under-recall of the SAR class even while overall accuracy holds — this is the model's single highest-cost failure mode and must have its own dashboard, not be inferred from blended metrics.
- Tracking of real-world analyst override rate (how often an analyst disposition disagrees with the model's recommended disposition), segmented by typology and disposition class, as a live proxy for drift not captured by the static golden sets.

**Escalation trigger:** Any blocking-threshold breach on a scheduled monitoring run, any Severity-1 groundedness defect, or an analyst-override rate spike (threshold to be set by the model risk function; not yet defined — open item) triggers model risk and AFC compliance notification within 1 business day.

---

## WITHDRAWAL

The model must be withdrawn from production use — reverting triage to the pre-existing manual/legacy process — upon any of the following:

1. **Quality-floor breach with 1-hour kill-switch.** A Severity-1 defect (fabricated evidence citation, i.e., a cited transaction ID or account attribution that does not exist in the source context) detected in production. Per the security review's stated control, this triggers withdrawal of the affected configuration within 1 hour of detection.
2. **Blocking-threshold breach on scheduled re-evaluation.** Disposition accuracy falls below 0.92 on `GOLD-600`, or the (to-be-set) `ESCALATE_SAR_RECOMMEND` recall threshold is breached, on any quarterly refresh or ad hoc re-run.
3. **Demonstrated successful prompt injection in production** that changes `disposition` or `typology_assessment`, or causes injected text to appear in `rationale` as a stated finding — i.e., an ASR event observed live, not just in `ADV-SET` testing.
4. **Scope violation.** Any evidence that the model, or an integration around it, has acted beyond the advisory role (auto-closed an alert, produced output consumed by a system outside the authorized case-management queue, or caused SAR-related narrative to reach an unauthorized channel — T-4/T-6).
5. **Unresolved go-live gaps past the committed remediation date.** If any of the open items below is not resolved by its committed date, the affected component may not go live, and if already live, must be withdrawn: (a) numeric blocking/warning thresholds for groundedness, ASR, and cost; (b) programmatic (non-prompt) enforcement of the 140-character injection cap; (c) documented and tested row-selection algorithm for transaction-history truncation; (d) deterministic schema-validation-failure fallback; (e) decoding-parameter fixation and test-retest consistency metric.
6. **Regulatory or legal determination** that the model's role, data handling, or output distribution no longer satisfies applicable BSA/AML program requirements, independent of any technical metric.

**Withdrawal mechanics:** Revert to the pre-model manual alert-triage process for all affected alert volume; do not route traffic to a lower-reviewed prior model version as a substitute without its own current, valid sign-off. Document the triggering condition, detection time, and withdrawal time in the model risk incident log for examiner review. Re-entry to production requires a full re-run of the E-1 gate against the version that caused withdrawal, with the specific failure mode added as a named regression test before any re-approval.

---

**Open items blocking full model risk sign-off** (carried forward from the code review; this document does not resolve them, it records them as conditions of approval): truncated pass-threshold table, undocumented schema-validation-failure behavior, prompt-only (non-enforced) injection cap, undocumented row-truncation algorithm, no determinism/consistency test, no standalone SAR-recall threshold, ambiguous enforcement point for `data_gaps` conditional-mandatory logic. This model is **conditionally approved for a limited pilot only** (shadow mode, analyst-reviewed, no auto-close) pending closure of these items; it is not approved for unsupervised production triage.