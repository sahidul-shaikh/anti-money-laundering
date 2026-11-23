# Alert Triage Agent — Architecture

## COMPONENTS

**C1. Alert Ingestion Service**
Polls/subscribes to the alert store (transaction-monitoring system, sanctions-screening engine, high-risk-customer-review queue) for new/updated alerts. Normalizes alert metadata, customer profile, transaction records, free-text fields, and prior case notes into a single internal `AlertBundle` schema. Read-only against source systems. No model inference occurs here.

**C2. Untrusted-Text Sanitizer / Tagger**
Receives the `AlertBundle`. Extracts every field known to originate outside bank control — wire OBI line, SWIFT 70/72, ACH addenda, check-memo OCR, sanctions fuzzy-match justification text — and wraps each in an explicit `<untrusted_data source="...">` delimiter with provenance metadata (source system, field name, ingestion timestamp). This is the only component permitted to construct the prompt payload that crosses into the model context; it does not interpret the text, only delimits and labels it. Implements control T-1 at the data layer.

**C3. Evidence Retriever**
Given an `AlertBundle`, pulls supporting structured evidence: linked transaction history, counterparty risk data, prior alerts on the same customer, QA findings. Returns record IDs alongside content, so every fact the model sees is independently citable (feeds AC-4's "cited transaction/evidence record IDs" requirement).

**C4. Triage Model (LLM core)**
Receives (a) structured, trusted fields directly, and (b) delimited untrusted text from C2, under a system prompt that states untrusted-delimited content is data only, never instruction. Produces a candidate disposition (`auto-close` / `escalate-to-investigation` / `insufficient-data`), confidence score, reasoning trace, and list of cited record IDs. Stateless per invocation; no memory of prior model calls beyond what C3 retrieves.

**C5. Injection/Contradiction Detector**
Runs in parallel with, or immediately after, C4. A narrower-purpose classifier (can be a second, smaller model call or a deterministic pattern/semantic check) scanning untrusted fields for imperative-mood strings directed at an AI/system/analyst ("ignore prior alerts," "auto-approve," "pre-approved by compliance"). On detection, forces a `flag: contradiction_detected` attribute onto the output regardless of C4's own disposition. Implements FR-6 and is the component directly tested by AC-6.

**C6. Output Validator**
Deterministic, non-model code. Rejects any C4 output missing a required rationale field (typology code, cited record IDs, confidence score, model/prompt version) per AC-4. Rejects any disposition that resolves a C5-flagged contradiction into `auto-close` without an explicit override reason — there is none available, so these are forced to `escalate-to-investigation` or `insufficient-data`. This is a hard gate: outputs failing validation never reach the review queue.

**C7. Confidence Threshold Router**
Deterministic. Compares C4's confidence score against the calibrated auto-close threshold (tuned against AC-2's 98.5% precision target). Alerts below threshold are forced to `insufficient-data` or `escalate-to-investigation`, never `auto-close`, independent of what C4 recommended.

**C8. Review Queue / Write Store**
The only system-of-record write target the agent touches. Stores the disposition proposal, rationale object, confidence, model/prompt version, and (where applicable) draft SAR narrative watermarked `DRAFT — NOT FILED — PENDING BSA OFFICER REVIEW`. Append-only; the agent has no update/delete grant here or anywhere else (FR-4).

**C9. SAR Drafting Module**
Invoked only on explicit analyst request against an already-escalated alert. Produces narrative text from the same evidence bundle. Writes exclusively to C8 with the draft watermark set at write time by C8's schema, not by the model's own claim — the watermark field is non-model-writable. Satisfies AC-5.

**C10. Audit/Observability Log**
Immutable log of every C4/C5/C6/C7 decision, every validator rejection, every analyst override, and every BSA Officer electronic-signature event. Feeds the MRM monthly fair-lending/precision review and the AC-1/AC-2/AC-3 measurement pipeline.

## DATA FLOW

1. Alert lands in source systems (TM alert store, sanctions screening, high-risk-review queue). **C1** pulls it, assembles the `AlertBundle`.
2. **C2** separates trusted fields (alert ID, risk score, KYC data, transaction amounts/timestamps/channels, rule/typology code) from untrusted free text (OBI, SWIFT 70/72, ACH addenda, memo OCR, fuzzy-match justification) and delimits the latter.
3. **C3** retrieves supporting evidence with record IDs; attaches to the bundle.
4. The composed, delimited payload crosses the trust boundary into **C4** (model inference). This is the single crossing point referenced below.
5. **C4** emits: disposition, confidence, rationale, cited record IDs, reasoning trace.
6. In parallel, **C5** independently scans the untrusted fields and emits a contradiction flag, keyed to the same alert ID — this output is deterministic-adjacent and does not depend on C4 having "noticed" the injection itself.
7. **C6** merges C4 + C5 outputs. Validates schema completeness (AC-4). Forces non-auto-close on any unresolved contradiction.
8. **C7** applies the calibrated confidence threshold, downgrading low-confidence `auto-close` calls.
9. Final proposal writes once, append-only, to **C8**. Nothing upstream of C8 can modify a case, release a hold, contact a customer, or file a SAR (FR-4) — there is no code path from C4/C5/C6/C7 back into source-of-record systems.
10. Level 1 analyst reads from C8, accepts/overrides/escalates. On override, the decision and reason are written back to C8 and C10, never back into C4's context (no feedback loop that lets analyst corrections silently retrain or prompt-steer production inference without a review gate).
11. If the analyst requests SAR drafting, **C9** runs against the already-escalated alert's evidence bundle and writes a watermarked draft to C8.
12. BSA Officer reviews via the case-management system (downstream, out of scope) and signs; the signature event is logged to **C10**, which is the only path to an actual filed SAR.
13. **C10** feeds nightly/monthly batch jobs computing AC-1 (false-negative rate), AC-2 (precision), AC-3 (disagreement rate) against QA ground truth, and the AC-6 injection fixture suite is run as a pre-deployment and periodic regression gate against C2 through C7 as a unit.

## TRUST BOUNDARIES

**Primary boundary: external free text → model context, at the C2 → C4 edge (step 4 above).**
Everything originating outside the bank's direct control — counterparty-authored OBI/SWIFT/ACH/memo text, and screening-vendor fuzzy-match justification strings — is untrusted regardless of which internal system stores it. This is the one boundary crossing in the architecture where adversary-controlled content enters the model's context window, and it is where T-1 (prompt injection via alert free text) lives. Controls at this boundary:
- C2 delimits and tags provenance before the text ever reaches C4; the system prompt instructs the model that delimited content is data, never instruction.
- C5 runs an independent detector that does not rely on C4 self-reporting that it was targeted — this avoids a single point of failure where a successfully-injected C4 could also suppress its own flag.
- C6 is a non-model gate: even a fully-compromised C4 output cannot reach `auto-close` if C5 raised a flag, because C6's override logic is deterministic code, not another model call.
- AC-6's fixture suite (50+ injection strings, disposition-invariance test) is the acceptance gate for this boundary specifically, and is re-run on every prompt/model version change (tracked via the version identifier in the rationale object).

**Secondary boundary: model output → system of record, at the C7 → C8 edge.**
This is a human/write-authority boundary, not a data-trust boundary: C4's output is always treated as an unauthenticated proposal, never a command, no matter how high its stated confidence. Controls:
- C8 is append-only and is the sole write surface the agent has (FR-4); there is no credential or API path from C4/C9 to the case-management system, hold-release system, SAR e-filing system, or customer-contact systems.
- The `DRAFT — NOT FILED` watermark on SAR narratives is set by C8's schema/write path, not asserted by the model — a prompt-injected or hallucinated claim of "approved, file now" inside C9's output has no mechanism to change filing status.
- Actual SAR filing requires a BSA Officer electronic-signature event logged in C10, a boundary the agent has no identity or credential to cross.

**Tertiary boundary: analyst override → model context.**
Analyst corrections recorded in C8/C10 are read by offline MRM/retraining review processes, not re-injected into live C4 inference. This prevents an adversary from laundering injected instructions through a compromised or socially-engineered analyst action back into the model's trusted-context assumptions.