# Architecture Decision Records

| | |
|---|---|
| **Document ID** | AMLI-ADR-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Solution Architect |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

Each record states the context, the decision, the alternatives considered and
the consequences — including the ones we dislike. A decision is not reopened
without a new record superseding it.

| ADR | Title | Status |
|---|---|---|
| 001 | Relational system of record | Accepted |
| 002 | Amazon Bedrock behind a single gateway | Accepted |
| 003 | Evidence-gated model routing | Accepted |
| 004 | Deterministic groundedness, not LLM-as-judge | Accepted |
| 005 | Destructive scopes are unregisterable | Accepted |
| 006 | Untrusted-data envelope at the boundary | Accepted |
| 007 | Thresholds extracted into a versioned catalogue | Accepted |
| 008 | `AI_RUN` as the single join key | Accepted |
| 009 | Configuration is a versioned asset, not a setting | Accepted |
| 010 | Outcome, adjudication and label stored separately | Accepted |
| 011 | Evidence as hashed write-once objects | Accepted |
| 012 | Graph projection deferred, not designed out | Accepted |
| 013 | Actimize remains authoritative | Accepted |
| 014 | Jurisdiction isolation by row-level security | Accepted |
| 015 | Retrieval for rules and narratives, not for transactions | Accepted |
| 016 | Durable orchestration for batch, in-process for interactive | Accepted |
| 017 | One trace identifier across services and model calls | Accepted |
| 018 | Core thirteen entities first, full reference model as target | Accepted |

---

## ADR-001 — Relational system of record

**Status** Accepted · **Date** 2026-11-18 · **Deciders** Solution Architect, Data Architect

**Context.** The investigation record is intensely relational: alerts to cases
many-to-many, parties to accounts through roles, findings to evidence with
stance, decisions superseding decisions. It must support referential integrity,
point-in-time reconstruction and row-level jurisdiction scoping, and it must be
queried by auditors who are not engineers.

**Decision.** Aurora PostgreSQL 16 is the system of record for all investigation
data. Object storage holds evidence payloads; the database holds their hashes
and metadata.

**Alternatives.** A document store was considered and rejected: the integrity
constraints in AMLI-DM-001 §5 are the product, not an inconvenience. A graph
database as primary store was rejected for the same reason — see ADR-012.

**Consequences.** Schema migrations become a managed, reviewed activity.
Relationship rules are enforceable in the database rather than hoped for in
application code. Analytical graph queries need a projection (ADR-012).

---

## ADR-002 — Amazon Bedrock behind a single gateway

**Status** Accepted · **Deciders** Solution Architect, Security Architect

**Context.** Inference must stay in the approved region, must not train on
customer data, must be cost-accounted per call, and must be replaceable.

**Decision.** All inference goes to Amazon Bedrock through the Converse API, and
**exactly one component — the LLM Gateway — may open a provider connection.**
Model identifiers are pinned; a provider version change is treated as a release.

**Alternatives.** Direct SDK calls from the runtime were rejected: token
accounting, spend caps, fallback and prompt capture would then be duplicated in
every call site and would drift.

**Consequences.** An architecture test asserts that no other module imports the
provider SDK. Provider replacement (NFR-076) becomes a change in one component.
The gateway is a single point of failure and is therefore stateless and
horizontally scaled.

---

## ADR-003 — Evidence-gated model routing

**Status** Accepted · **Deciders** Solution Architect, Model Risk Lead

**Context.** The cheapest serving model is correct most of the time and cheap
every time. Using it always is wrong; using the expensive model always is
wasteful. A selection signal is needed that does not require the answer key.

**Decision.** Start at the cheapest serving model above the quality floor.
**Escalate once when the answer cites no evidence, or cites a reference that is
not in the captured evidence.** The signal is computed from the answer itself
with no label and no judge model.

**Evidence.** On the reference implementation's recorded baseline, the cheap
tier returned no citable evidence on 12 of 61 clean alerts and was wrong on 67%
of those against a 22% base rate. "Answered with nothing to point at" is a real
signal.

**Alternatives.** Self-reported confidence was rejected as poorly calibrated and
gameable. A second model as judge was rejected under ADR-004. Always-premium was
rejected on cost without quality benefit on the grounded majority.

**Consequences.** Worst-case latency and cost are roughly double the cheap path,
bounded by the escalation limit (FR-036) and the spend cap (FR-037). The routing
policy is itself a versioned asset and any change to it goes through the gate.

---

## ADR-004 — Deterministic groundedness, not LLM-as-judge

**Status** Accepted · **Deciders** Model Risk Lead, Solution Architect

**Context.** We must know whether a claim is supported. The common approach is a
second model scoring the first.

**Decision.** Groundedness is computed by resolving each cited reference against
the evidence captured for that run. A reference is present or it is not. No
model participates in the judgement.

**Alternatives.** LLM-as-judge was rejected: it introduces a second unvalidated
model into a regulated control path, it is not reproducible, it cannot be
explained to a validator, and it fails in correlated ways with the model it
judges.

**Consequences.** The check is a pure function with unit tests and no inference
cost. It only verifies *existence* of the cited reference, not the soundness of
the inference drawn from it — that remains a matter for the human reviewer and
for outcome analysis. We state that limitation explicitly rather than implying
groundedness means correctness.

---

## ADR-005 — Destructive scopes are unregisterable

**Status** Accepted · **Deciders** Security Architect, MLRO

**Context.** An agent that can close an alert is, if it can be steered, a
laundering instrument. Permission systems fail: a scope gets granted for a
migration, a persuaded operator enables it, a bug bypasses the check.

**Decision.** The capabilities `alert.close`, `case.delete`, `sar.file`,
`party.write`, `payment.release` and `watchlist.write` are **not registerable**
in the tool registry. Attempting to register one raises at start-up and the
service does not come up.

**Alternatives.** Role-based denial was rejected: it is one configuration error
away from being wrong, and it leaves the capability present in the binary.

**Consequences.** A future product decision to allow automated closure is a
code change with a design review, not a permission grant. That is the intent.
The start-up assertion is itself a tested control (FR-041).

---

## ADR-006 — Untrusted-data envelope at the boundary

**Status** Accepted · **Deciders** Security Architect

**Context.** Payment reference and remittance free text is written by the
remitter and travels unmodified into the prompt. It is the only genuinely
attacker-controlled input in the pipeline.

**Decision.** Such text is marked untrusted at ingestion and, at render time, is
enclosed in explicit delimiters with a preamble stating it is data written by a
third party, to be reported as evidence and never followed as instruction.

**Evidence.** Paired A/B probing in the reference implementation — identical
alert, model and payload, differing only in whether the envelope is applied —
shows the framing is the determining variable.

**Alternatives.** Stripping or sanitising the text was rejected: the text is
itself evidence, and in a structuring investigation its content may matter.
Classifier-based filtering was rejected as a *sole* control because it fails
open on novel phrasing; it is retained as a detection signal (FR-089).

**Consequences.** The envelope consumes tokens on every call. Prompts must be
rendered through one code path — ad-hoc string assembly bypasses the control, so
rendering is centralised and tested.

---

## ADR-007 — Thresholds extracted into a versioned catalogue

**Status** Accepted · **Deciders** Solution Architect, Compliance

**Context.** Detection thresholds originated as prose inside a system prompt,
transcribed by a person from a 677-page vendor specification. Nothing kept them
current and nothing recorded their provenance.

**Decision.** Thresholds are extracted into a versioned catalogue, each entry
carrying its rule identifier, source document and page. The agent retrieves the
version in force for the alert's scenario and date, and the citation travels
with it into the prompt.

**Consequences.** Reduced prompt size and a verifiable provenance chain. The
extraction job becomes a maintained asset with a diff on every rebuild
(FR-014). Institution-specific overrides are recorded against the vendor
default rather than replacing it (FR-018).

---

## ADR-008 — `AI_RUN` as the single join key

**Status** Accepted · **Deciders** Solution Architect, Data Architect

**Context.** Build, run, secure and improve produce records that are routinely
kept in separate stores. The consequence is that "one governed loop" is an
assertion nobody can query.

**Decision.** `ai_run` is the integration record. Every model call, tool call,
control check, security event, evidence access, finding and piece of feedback
carries `run_id`. Evaluation runs and change approvals join the same spine.

**Alternatives.** Per-pillar identifiers correlated later by timestamp were
rejected: correlation by time is lossy under concurrency and unusable in audit.

**Consequences.** `ai_run` is on the write path of nearly everything and is
therefore partitioned and indexed accordingly. The reference implementation
satisfies this only for model calls; closing the gap for security and
evaluation records is explicit scope in Phase 2 of AMLI-PLAN-001.

---

## ADR-009 — Configuration is a versioned asset, not a setting

**Status** Accepted · **Deciders** Model Risk Lead, Head of FinCrime Technology

**Context.** Prompts, routing policy, thresholds and guardrail policy change
behaviour as much as code. A runtime toggle on any of them is an unvalidated
model change.

**Decision.** Each is an `ai_asset` with versions carrying a content hash.
Changes are assembled into a candidate release, evaluated, approved and
deployed. There are no runtime toggles for model, prompt, policy or threshold.

**Consequences.** Even a one-word prompt fix needs a release — deliberately.
Release cadence must therefore be fast and cheap, which is a pipeline
requirement, not an argument against the decision (NFR-066, NFR-067).

---

## ADR-010 — Outcome, adjudication and label stored separately

**Status** Accepted · **Deciders** Model Risk Lead, Product Owner

**Context.** In the supplied extract every alert escalated and filed: 25 SARX,
9 CTR, 1 CTRX. Labelling "filed = should escalate" would score an
escalate-everything agent at perfect recall. A CTR is a threshold obligation,
not a finding of suspicion. Equally, a closed alert is weak evidence of
innocence.

**Decision.** Three fields, never conflated: `outcome` (what the institution
did, always known), `adjudication` (what a qualified reviewer concluded,
recorded separately), and `label` with `label_basis` and `label_confidence`
(what is used for scoring). **Performance may be quoted only against adjudicated
labels, with the confidence basis stated.**

**Consequences.** An adjudication exercise is required before any defensible
accuracy claim — ASM-002 and a Phase 1 deliverable. Early reporting will cover
a smaller, honestly-qualified sample rather than a large contaminated one.

---

## ADR-011 — Evidence as hashed write-once objects

**Status** Accepted · **Deciders** Data Architect, Internal Audit

**Context.** A disposition must be defensible years later, when the source
systems have changed. A live reference proves nothing about what was seen.

**Decision.** Every consulted source is captured as an object in S3 with Object
Lock for the retention period, addressed by content hash, with capture
timestamp and source reference in the database. Evidence shown to a reviewer is
rendered from the snapshot, never re-queried.

**Consequences.** Storage grows at roughly 4 TB per year at reference volume.
Deduplication by content hash within an investigation mitigates this (FR-028).
Legal hold must interlock with the expiry job (FR-027).

---

## ADR-012 — Graph projection deferred, not designed out

**Status** Accepted · **Deciders** Solution Architect, Data Architect

**Context.** Two in-scope scenarios — multiple remitters to one beneficiary, and
shared identity attributes — are network questions. Network analysis is
naturally a graph workload.

**Decision.** The relational model carries the relationships explicitly
(`party_relationship`, `transaction_participant`, `party_account_role`), so the
information is present from day one. A graph projection is deferred to Phase 3
and introduced as a read-only derived store, never as a second source of truth.

**Consequences.** Phase 1 and 2 scenarios work without it. Phase 3 scenarios are
gated on counterparty data availability (DEP-004). We avoid operating two
authoritative stores, which is the common failure mode of graph adoption.

---

## ADR-013 — Actimize remains authoritative

**Status** Accepted · **Deciders** Head of FinCrime Technology, Solution Architect

**Context.** The institution already runs SAM for detection and ActOne for case
management, with regulatory history attached.

**Decision.** We ingest from SAM, enrich and reason, and write a recommendation
plus evidence pack back to the ActOne case record. **We never mutate alert or
case status in the source system.**

**Alternatives.** Replacing case management was rejected as disproportionate
scope with no benefit to the control objective.

**Consequences.** Two systems hold investigation state and must be reconciled —
a known operational cost, mitigated by idempotent write-back and a reconciliation
report (FR-074, RISK-009). A file-extract fallback is required for environments
without API access (FR-002).

---

## ADR-014 — Jurisdiction isolation by row-level security

**Status** Accepted · **Deciders** Security Architect, DPO

**Context.** Deployment spans up to four jurisdictions with different policies,
and cross-jurisdiction disclosure of customer data is a legal exposure.

**Decision.** One schema; every customer-bearing table carries
`institution_id` and `jurisdiction_code`; PostgreSQL row-level security
enforces scope from the session principal. Application code cannot opt out.

**Alternatives.** Database-per-jurisdiction was rejected for operational cost
and schema drift; application-only filtering was rejected because one missing
`WHERE` clause becomes a notifiable breach.

**Consequences.** Every query path must set the session context; this is done in
one connection-acquisition helper and tested. Cross-jurisdiction analytics
requires a deliberate, audited aggregation path.

---

## ADR-015 — Retrieval for rules and narratives, not for transactions

**Status** Accepted · **Deciders** Solution Architect

**Context.** Semantic retrieval is useful for unstructured policy and narrative
text. Transactions are structured and must be exact.

**Decision.** OpenSearch serves the rule catalogue and prior narrative
retrieval. **Transaction and party data is never retrieved semantically** — it
is selected relationally and supplied in full.

**Consequences.** No risk of an approximate match silently omitting a material
transaction. Retrieval quality problems are confined to explanatory material,
where an error degrades reasoning rather than falsifying evidence.

---

## ADR-016 — Durable orchestration for batch, in-process for interactive

**Status** Accepted · **Deciders** Solution Architect, SRE Lead

**Context.** The daily batch must survive instance loss, show its state and
retry safely. An interactive single-alert run must be fast.

**Decision.** Step Functions with SQS per stage for batch; a direct in-process
pipeline for interactive runs. Both execute the same runtime components and
write the same records.

**Consequences.** One behaviour, two drivers — a contract test asserts the two
paths produce identical records for the same input.

---

## ADR-017 — One trace identifier across services and model calls

**Status** Accepted · **Deciders** SRE Lead, Internal Audit

**Context.** Debugging and audit both need to follow one investigation across
services, queues, model calls and evidence accesses.

**Decision.** A `trace_id` is created at ingestion, propagated via
OpenTelemetry context, stored on `ai_run`, and emitted on every log line and
every provider request.

**Consequences.** Log lines carry an identifier that can be correlated to
customer data, so `trace_id` is treated as pseudonymous and the mapping is
access-controlled (NFR-047).

---

## ADR-018 — Core thirteen entities first, full reference model as target

**Status** Accepted · **Deciders** Data Architect, Solution Architect

**Context.** The reference logical model in `decks/AI_for_AI_AML.pptx` defines
roughly 45 entities across three domains. It is sound. Building all of it before
anything runs would delay every other outcome.

**Decision.** Implement thirteen core entities in Phase 1–2 — `alert`, `case`,
`case_alert`, `party`, `account`, `transaction`, `ai_run`, `evidence_item`,
`finding`, `finding_evidence`, `decision`, `actor`, `control_check` — and carry
the remainder as the specified target schema, phased in AMLI-PLAN-001.

**Rationale.** These thirteen satisfy five of the seven reference design
constraints and every *Must* functional requirement in the first release.

**Consequences.** Tables added later must not force restructuring of the core.
AMLI-DM-001 §7 records the extension points — principally
`report`/`report_version`, the asset and release registry, and
`party_relationship`/`transaction_participant` — so that later phases add rather
than rewrite.
