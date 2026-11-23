# Alert Triage Agent — Agent Graph and Loop

## LOOP

The agent runs one bounded, mostly-linear pass per alert — not an open-ended ReAct loop. There is exactly one place where it is allowed to iterate (evidence sufficiency), and every iteration is counted against a hard cap. This is a deliberate design choice: an AML triage agent that "keeps trying" until it likes its own answer is a model-risk and audit problem, not a feature.

**Goal** (set per invocation, one per `alert_id`): produce either (a) a schema-complete, threshold-checked disposition proposal written once to C8, or (b) a terminal `insufficient-data` / `escalate-to-investigation` proposal, within bounded time and bounded retries. The loop never has the goal "get to auto-close" — auto-close is an outcome, not a target.

**Act**: C3 retrieves evidence → C4 infers a candidate disposition + rationale + cited record IDs, while C5 independently scans untrusted fields for injection/contradiction in parallel.

**Verify**: C6 checks schema completeness and contradiction resolution (hard, deterministic gate); C7 checks C4's confidence against the calibrated auto-close threshold τ (initial τ = 0.85, retuned against the AC-2 98.5%-precision target at each monthly MRM review — see C10 feed). Both are non-model code; neither can be talked into passing by the model's own text.

**Iterate**: the only legal retry is "C4 declared `insufficient-data` because named evidence was missing" (e.g., it cites a record ID that C3 didn't return). In that case the loop goes back to C3 with the specific missing-evidence request and re-runs C4. Bound: **max 2 retries (3 total C4 invocations)** per alert. Retrying for any other reason (low confidence, contradiction flag, validator schema failure) is explicitly disallowed — those are terminal, not retryable, because re-running the model until the number looks better is itself an attack surface and a precision-inflation risk.

**Stopping conditions** (first one hit wins):
1. **Success-terminal**: C6 passes schema + contradiction checks, C7 clears (or forces) a disposition, C8 write succeeds. Loop ends, state closed.
2. **Retry-exhausted**: 3 C4 invocations reached without resolving an evidence gap → forced `insufficient-data`, write to C8, loop ends.
3. **Contradiction-terminal**: C5 raises `contradiction_detected` → next disposition is forced into `{escalate-to-investigation, insufficient-data}` by C6 on the very first pass; no retry attempted regardless of C4's confidence.
4. **Validator-hard-fail**: C6 rejects on missing required fields (typology code, cited record IDs, confidence, model/prompt version) a second time after one re-run → the alert does **not** get silently dropped or defaulted; it is routed to an engineering/ops exception queue (distinct from the analyst queue) and logged to C10. This is a code-path failure, not a disposition, and is never shown to the analyst as if it were a model opinion.
5. **Timeout**: end-to-end wall-clock budget of **120 seconds** per alert (covers C1→C8). On timeout, forced `insufficient-data`, reason code `timeout`, written to C8.
6. **No disposition ever reaches `auto-close` without passing both C6 and C7 on the same pass** — there is no retry path that lets a low-confidence or contradiction-flagged alert "try again" into auto-close.

The loop processes alerts independently and statelessly across invocations: nothing learned on alert A changes how alert B is evaluated except through C3's structured evidence (e.g., "prior alerts on same customer" is data, not model memory).

## NODES

| Node | Maps to | Input | Output | Retryable? |
|---|---|---|---|---|
| N1 Ingest | C1 | Source-system alert event | `AlertBundle` v0 (raw) | No — read-only pull, idempotent on alert_id+version |
| N2 Sanitize/Tag | C2 | `AlertBundle` v0 | `AlertBundle` v1: trusted fields + `<untrusted_data source=...>`-delimited fields | No — deterministic |
| N3 Evidence Retrieve | C3 | `AlertBundle` v1 (+ optional missing-evidence request from N4) | `AlertBundle` v2 with cited, record-ID-bearing evidence attached | Yes — up to 2 times, driven only by N4's explicit evidence gap |
| N4 Triage Infer | C4 | `AlertBundle` v2 | disposition, confidence, rationale, typology code, cited record IDs, reasoning trace | Invoked up to 3 times total (see loop); each invocation is stateless |
| N5 Contradiction Detect | C5 | Same untrusted fields as N4, run in parallel | `contradiction_detected: bool` + matched span(s), keyed to alert_id | No — deterministic-adjacent, always runs once per N4 invocation |
| N6 Validate (join) | C6 | N4 output + N5 output | pass/fail; on fail with resolvable cause → back to N3; on fail unresolved → ops exception queue; on contradiction → forced non-auto-close | Gate, not itself retryable |
| N7 Confidence Route | C7 | N6-passed output | final disposition (confidence ≥ τ and no flags → `auto-close` permitted; otherwise forced `insufficient-data`/`escalate-to-investigation`) | No |
| N8 Write Queue | C8 | N7 output | one append-only record: disposition, rationale, confidence, model/prompt version, evidence IDs | No — single write, no update/delete grant exists |
| N9 SAR Draft | C9 | Analyst-triggered request against an already-escalated N8 record | draft narrative, watermark `DRAFT — NOT FILED — PENDING BSA OFFICER REVIEW` set by C8's schema | Re-invocable on analyst request only; not part of the automated loop |
| N10 Audit Log | C10 | Every N4–N9 event, every validator rejection, every human action | immutable log entry | N/A — side-effect sink wired to every edge |

Edges: N1→N2→N3→(N4 ∥ N5)→N6. N6 → N3 (bounded retry, evidence-gap only) or N6 → N7 (pass) or N6 → ops exception queue (unresolved schema fail). N7 → N8 (always, exactly one write). N8 → N9 (human-gated, out-of-band). Every node → N10 (fan-out, unconditional).

## SHARED STATE

A single mutable `AlertBundle` object keyed by `alert_id` is threaded through N1–N7; it becomes immutable the instant it is written at N8. State fields:

- `alert_id`, `alert_version`, `source_system`, `ingested_at` (N1)
- `trusted_fields`: risk score, KYC data, transaction amount/timestamp/channel, rule/typology code (N1/N2)
- `untrusted_fields[]`: each with `content`, `source`, `field_name`, `ingestion_timestamp`, delimiter tag (N2) — these are never mutated after N2, only read
- `evidence[]`: record ID, record type, content, retrieval timestamp, retrieval attempt number (N3) — append-only across retries, never overwritten, so a later retry cannot silently erase what an earlier pass saw
- `model_outputs[]`: one entry per N4 invocation (bounded at 3) — disposition, confidence, rationale, cited IDs, model/prompt version, attempt number. All kept, not just the last, so the audit trail shows exactly what changed between retries and why
- `contradiction_flag`: bool + matched span + detector version (N5), sticky once set true — no downstream node can clear it
- `validation_result`: pass/fail + failure reason list (N6)
- `final_disposition`, `final_confidence`, `threshold_applied` (τ value used), `routing_reason` (N7)
- `queue_record_id`: assigned only at N8, the point at which the object becomes append-only/immutable
- `human_actions[]`: analyst accept/override/escalate, BSA officer signature event — written only to C8/C10, never back into `model_outputs[]` or re-fed as N4 input without a new, explicitly-gated alert cycle (prevents silent retrain/prompt-steer via analyst corrections)

No field is ever deleted; retries append rather than replace, so a model-risk reviewer can reconstruct, from shared state alone, every evidence gap and every re-inference without consulting a separate log.

## HUMAN GATE

1. **Pre-action gate on every non-auto-close disposition (mandatory)**: `escalate-to-investigation` and `insufficient-data` outputs sit in C8 until a Level 1 analyst accepts, overrides, or escalates. No code path from N1–N9 can act on a source-of-record system (hold release, customer contact, SAR filing) — FR-4 makes this gate structural, not optional.
2. **Mandatory, non-dismissable gate on contradiction flags**: any alert with `contradiction_detected = true` routes to analyst review with the matched injected span surfaced verbatim alongside the model's rationale. The analyst sees what the model saw; the flag cannot be cleared by re-running N4, and C6 will not let a contradiction-flagged alert resolve to `auto-close` under any confidence value.
3. **Retrospective sampling gate on auto-close**: even dispositions that clear N6+N7 and write `auto-close` are subject to a human-reviewed sample — initial rate **5% of auto-closes, risk-stratified upward for any typology code with fewer than 50 historical auto-closes** — feeding the AC-2 precision measurement in C10. This is the gate that keeps the "no human in the loop" path honest after the fact rather than before it.
4. **BSA Officer electronic signature gate before any SAR leaves draft state**: C9 output is never filing-eligible on its own; a named BSA Officer must review and electronically sign in C8 before the narrative can move to actual filing systems (outside this agent's write scope). The `DRAFT — NOT FILED — PENDING BSA OFFICER REVIEW` watermark is schema-enforced, not model-claimed.
5. **Engineering/model-risk gate on recurring validator failures**: an alert that fails N6 schema validation twice routes to an ops exception queue, not to the analyst queue and not to a silent default disposition — this is a system-health signal, and burying it in the normal review queue would hide a C4/C6 contract break from the people who need to fix it.
6. **Monthly MRM review gate on τ and on C5's detector**: threshold recalibration (τ) and contradiction-detector tuning are human-approved changes, logged to C10, never a runtime/self-adjusting parameter the agent changes on its own.