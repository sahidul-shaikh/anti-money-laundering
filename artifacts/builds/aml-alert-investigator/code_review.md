# AML Alert Triage Agent — Code Review (C-4 Implementation Note + E-1 Evaluation Design)

Reviewed as a senior engineer against the supplied C-4 implementation note and E-1 evaluation design. Both documents were delivered truncated (C-4 cuts off mid-definition of `data_gaps`, field 9 is never shown; E-1's pass-threshold table cuts off after the first row). That incompleteness is treated as finding #1 below, not papered over.

## FINDINGS

**1. Both source documents are truncated before the control section closes.**
C-4 cuts off mid-sentence on field 8 (`data_gaps`): "Mandatory non-empty when `disposition = ESCALATE_` …" — field 9 is never shown at all. E-1's pass-threshold table is cut off after a single row, so every blocking/warning number for groundedness, robustness (ASR), and cost is unknown. A review cannot sign off on a spec it hasn't seen in full.
*Remedy:* Re-issue both documents complete. Do not treat this review as covering field 9 of the schema or any threshold beyond disposition accuracy — those are unreviewed, not approved.

**2. No defined behavior for schema validation failure at generation time.**
The system prompt instructs the model to always emit conformant JSON, but C-4 never states what the parsing/validation pipeline does when it doesn't — malformed JSON, wrong enum value, missing mandatory field, extra fields, `alert_id` mismatch. Is there a retry? A forced fallback to `ESCALATE_INSUFFICIENT_DATA`? Does it page a human? Without this, a parsing failure in production has an undefined failure mode, which for a system feeding SAR decisions is not acceptable.
*Remedy:* Specify a deterministic fallback (e.g., one bounded retry with a stricter format reminder, then hard-fail to `ESCALATE_ANALYST_REVIEW` with `data_gaps: ["schema_validation_failed"]`, logged and alerted). Confirm whether provider-level constrained decoding / structured outputs is used to make this failure mode rare in the first place — the note is silent on whether generation is free-form-then-parsed or schema-enforced at decode time.

**3. The 140-character injection-quoting cap appears to be a prompt instruction, not an enforced control.**
The rationale's cap on verbatim `user_free_text:*` content is the stated mitigation for the one identified prompt-injection boundary, but C-4 never says this is mechanically truncated/checked by the parsing pipeline before the response leaves C-4 — it reads as something the model is told to do. A security control for adversary-controlled input cannot rely solely on the same model's instruction-following; that's the exact thing the threat model distrusts.
*Remedy:* Enforce the cap programmatically post-generation (truncate or reject responses exceeding cumulative 140 chars of verbatim `user_free_text:*` content, measured by substring match against the actual context sent), not just by prompting. E-1's "injection leakage check" should then be testing the enforcement code path, not just the model's compliance rate.

**4. No dedicated, asymmetric metric for missed SAR recommendations.**
E-1 gates on 4-way disposition accuracy and macro-F1. In AML triage the costly error is a false negative on `ESCALATE_SAR_RECOMMEND` (a missed SAR is a regulatory filing failure); a false positive (unnecessary analyst review) is comparatively cheap. Macro-F1 and overall accuracy do not surface this asymmetry — a model could clear 0.92 accuracy while quietly under-recalling the ~3%-base-rate SAR class, which is exactly the class E-1 says is highest-cost to get wrong.
*Remedy:* Add a standalone blocking metric: recall (sensitivity) on `ESCALATE_SAR_RECOMMEND` within `GOLD-600`, and separately within `GOLD-150`, with its own threshold independent of macro-F1 and tighter than the all-class average. Report the confusion matrix, not just aggregate scores.

**5. Context truncation row-selection strategy is unspecified.**
C-4 states transaction history is capped at ≤500 rows with a truncation flag, but never says which 500 rows are kept (most recent, highest amount, random, stratified). Structuring patterns are frequently built from many small transactions that could be exactly the rows dropped by a naive "most recent" or "highest amount" selection. E-1's robustness family (3b) tests "truncation at 500 rows with flag set" but can't meaningfully validate against an adversarial or representative case without knowing the selection rule, since the test fixture and production behavior could diverge.
*Remedy:* Document the row-selection algorithm in C-4 and make `ADV-SET`'s truncation cases exercise that exact algorithm (not a placeholder), including a case specifically engineered to hide a structuring pattern outside the retained window.

**6. No consistency/determinism check on repeated runs of the same alert.**
The eval identifies a run by `(prompt_version, model_id, context_schema_version)` but omits decoding parameters (temperature, top_p, seed) from both that triple and from any measured property. For a system whose output can trigger a SAR filing, the same alert context should produce a stable disposition on repeat invocation; no test measures this.
*Remedy:* Add decoding parameters to the run identity triple, fix temperature to a low, documented value for production, and add a test-retest consistency metric (e.g., N=5 reruns per `GOLD-150` alert, require ≥X% disposition agreement) to the correctness family.

**7. Conditional-mandatory field logic (`data_gaps`) has no stated enforcement point.**
Per finding #1 the sentence is truncated, but even the visible fragment ("mandatory non-empty when disposition = ESCALATE_…") describes a cross-field constraint that ordinary JSON-schema validation can't express without a custom rule. It's unclear whether C-4's validation pipeline actually checks this conditional or just documents it as an expectation of the model.
*Remedy:* State explicitly that this is a post-generation validation rule (not just a prompt instruction) and specify the fallback when violated (same question as finding #2).

**8. PII/BSA-data handling in the eval store is unaddressed.**
`GOLD-600`/`GOLD-150` are drawn from real historical alerts with real customer PII, SAR-relevant narrative, and screening data; the eval store is described as append-only but nothing is said about access control, encryption at rest, retention limits, or masking of `user_free_text:*` content in logged eval records. This is BSA/SAR-adjacent data at a US retail bank — mishandling it is a compliance exposure independent of model behavior.
*Remedy:* Add a data-handling section: who can query the eval store, retention period, whether raw memo/counterparty text is redacted or tokenized in stored eval artifacts, and whether the sequestered `GOLD-150` set has tighter access controls than `GOLD-600`.

**9. Golden-set label quality and enum-drift governance not specified.**
No inter-annotator agreement figure is given for the "human-adjudicated" labels in `GOLD-600`/`GOLD-150`. Separately, `typology_assessment` is validated against "the fixed TMS typology codes... known to C-4," but there's no owner or process for keeping that enum, the golden set's typology labels, and the live TMS system in sync as typologies are added/retired upstream.
*Remedy:* Report IAA (e.g., Cohen's kappa) for the adjudication process and name an owner/process for enum version bumps that ties to the `context_schema_version` axis already used for run identity.

**10. Claim-coverage audit sample size is asserted, not justified.**
The 10% human-audit sample for claims the automated extractor misses has no stated confidence target (margin of error, or minimum claims audited per release). At low release volume this could be a handful of sentences.
*Remedy:* Define a minimum absolute audit count per release (not just a percentage) and a target precision/recall for the extractor itself, validated once against a hand-labeled subset.

## SEVERITY

| # | Finding | Severity |
|---|---|---|
| 1 | Documents truncated before control sections close | High (review scope) |
| 2 | No defined behavior on schema validation failure | High |
| 3 | Injection-quoting cap looks instruction-only, not enforced | High |
| 4 | No dedicated recall metric for missed SAR recommendations | High |
| 5 | Truncation row-selection strategy unspecified | Medium-High |
| 6 | No determinism/consistency check across reruns | Medium |
| 7 | Conditional-mandatory `data_gaps` enforcement point unclear | Medium |
| 8 | PII/BSA data handling in eval store unaddressed | Medium-High |
| 9 | Golden-set label quality / enum-drift governance missing | Medium |
| 10 | Claim-coverage audit sample size unjustified | Low-Medium |

## BLOCKING

I would block promotion to production on findings **1, 2, 3, 4, and 5**:

- **Finding 1** blocks outright — I cannot approve a spec whose output schema and pass thresholds are not fully visible. Re-issue complete documents before further sign-off.
- **Finding 2** blocks because an undefined failure mode on a validation reject, in a pipeline that feeds SAR-adjacent decisions, is not an acceptable production state regardless of how rare it is expected to be.
- **Finding 3** blocks because the only stated mitigation for the one identified prompt-injection vector is, on the evidence given, a soft instruction rather than an enforced post-generation check — this is the precise failure the threat model exists to prevent.
- **Finding 4** blocks because the evaluation design, as described, can pass its headline accuracy gate while silently under-recalling the highest-cost class (missed SARs). A model-risk reviewer should not accept aggregate accuracy as sufficient evidence of safety for the SAR-recommend class.
- **Finding 5** blocks because the robustness eval for context truncation is untestable in any meaningful way until the row-selection algorithm is specified — right now the test and the production behavior are not provably the same thing.

Findings 6–10 are real gaps that should be fixed before general availability but would not, on their own, stop a limited pilot with human-in-the-loop review of every `ESCALATE_*` disposition.