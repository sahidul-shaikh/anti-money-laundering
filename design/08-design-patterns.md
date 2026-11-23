# Design Patterns Register

| | |
|---|---|
| **Document ID** | AMLI-PAT-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Engineering Lead |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

A pattern is recorded here only where it is actually applied and where the
choice was not obvious. Patterns considered and rejected are in §7, because the
rejections carry as much information as the adoptions.

---

## 1. Architectural patterns

### 1.1 Hexagonal architecture (ports and adapters)

**Applied to** the whole service. The domain — alert, case, evidence, finding,
decision, run — depends on nothing outside itself. Everything external enters
through a port.

| Port | Adapters |
|---|---|
| `AlertSource` | `ActimizeApiAdapter`, `FileExtractAdapter`, `InMemoryAdapter` (test) |
| `CaseSink` | `ActOneAdapter`, `NullSink` (dev) |
| `ModelProvider` | `BedrockAdapter`, `StubProvider` (test), future `AzureOpenAIAdapter` |
| `EvidenceStore` | `S3EvidenceStore`, `LocalFileStore` (test) |
| `RuleCatalogue` | `OpenSearchCatalogue`, `JsonFileCatalogue` |
| `Ledger` | `PostgresLedger`, `InMemoryLedger` (test) |

**Why.** NFR-076 and NFR-077 require the provider and the detection source to be
replaceable. Hexagonal makes that a stated contract with contract tests rather
than an aspiration. It also makes the domain testable without AWS.

**Enforced by** an architecture test asserting the domain package imports no
adapter, no SDK and no framework.

### 1.2 Layered persistence with a single ledger writer

**Applied to** all cost, quality and telemetry derivation. One component writes
`model_call` and `outcome`; every figure anywhere is computed from those rows.

**Why.** Principle P-1. The common failure is cost computed in the runtime and
again in a reporting job, which then disagree in front of a regulator.

### 1.3 CQRS-lite

Write models are normalised and constraint-enforced. Read models for the
reviewer workspace and the MI dashboards are materialised views refreshed on a
schedule, because an investigation screen joins eight tables and must return in
1.5 s (NFR-004).

**Deliberately "lite":** no separate event store, no eventual-consistency
semantics exposed to the user. Materialised views only.

---

## 2. Domain patterns

### 2.1 Strategy — model routing

`RoutingPolicy` is a strategy with parameters (`quality_floor`,
`escalate_without_evidence`, `min_groundedness`, `max_escalations`). The policy
is a versioned asset (ADR-009), so changing routing is a release that goes
through the gate — not an `if` statement someone edits.

### 2.2 Chain of responsibility — guardrails

Guardrails are an ordered chain, each returning `allow`, `block` or `escalate`,
each writing a `control_check`. Pre-call chain: input classification, envelope
assertion, scope assertion, spend check. Post-call chain: tipping-off guard,
egress classification, PII assertion on telemetry-bound fields.

**Why.** Controls must be individually auditable and individually testable. A
single monolithic `validate()` cannot answer "which control blocked this, under
which policy version".

### 2.3 Specification — rule evaluation

Detection rule predicates (band membership, window containment, occurrence
threshold, direction filter) are composable specification objects built from the
catalogue entry, not hand-written per scenario.

**Why.** FR-018 requires institution overrides on vendor defaults. Composable
specifications let an override replace one parameter without forking a rule.

### 2.4 Template method — the investigation pipeline

The run sequence (capture → resolve → render → guard → route → call → parse →
ground → persist) is fixed. Scenario-specific behaviour is supplied as hooks.

**Why.** ADR-016 requires the batch and interactive drivers to produce identical
records. A fixed skeleton with hooks makes that structural rather than
disciplinary, and a contract test asserts it.

### 2.5 Value objects and immutability

`Money`, `TransactionReference`, `Citation`, `ContentHash`, `JurisdictionCode`
are immutable value objects with validation at construction. Domain entities are
frozen; state changes produce new records (see 2.6).

**Why.** `Money` as a float is the classic defect in financial systems.
Construction-time validation means an invalid reference cannot exist in memory,
let alone be persisted.

### 2.6 Event sourcing — for decisions only

Full event sourcing is not used. Decisions and audit events are append-only with
explicit supersession (`decision.supersedes`), giving reconstructability where
it is required without imposing event-sourced complexity on the whole model.

**Why.** NFR-029 and FR-066 need decision history. The rest of the model does
not need it and would pay for it.

---

## 3. Integration and reliability patterns

| Pattern | Applied to | Why |
|---|---|---|
| **Adapter** | Actimize SAM, ActOne, KYC, Bedrock | Vendor interfaces change; the domain must not |
| **Anti-corruption layer** | Actimize ingestion | Source field names and semantics do not leak into the domain model; mapping is explicit and tested (AMLI-INT-001 §4) |
| **Outbox** | Domain write + event emission | A recommendation and its "ready for write-back" event commit in one transaction; a relay publishes. Prevents the recommendation existing without the event, or the reverse |
| **Idempotency key** | Every mutating API, every write-back | FR-040, FR-074. Keys held in Redis with a TTL exceeding the maximum retry window |
| **Retry with exponential backoff and full jitter** | Provider calls, source polling, write-back | Jitter is specified because synchronised retry after a provider blip is how a transient failure becomes an outage |
| **Circuit breaker** | Per provider, per model | An open circuit routes to fallback (FR-038) rather than queueing behind a failing dependency |
| **Bulkhead** | Separate task pools and queues for batch and interactive | A batch backlog must not starve a reviewer's interactive run |
| **Dead letter queue** | Every queue | NFR-028: bounded attempts then quarantine. Nothing retries forever |
| **Saga (orchestrated)** | Batch investigation workflow via Step Functions | Long-running, needs visible state and compensating cleanup of partial runs |
| **Transactional write-once** | Evidence capture | Object written and hash recorded; the database row is committed only after the object is durable |

---

## 4. Security patterns

| Pattern | Applied to | Why |
|---|---|---|
| **Capability unregisterable** | Destructive tool scopes | ADR-005. Stronger than deny-by-default: the capability does not exist to grant |
| **Trusted/untrusted data segregation** | Payment reference text | ADR-006. The envelope is applied at one render boundary so it cannot be bypassed by ad-hoc prompt assembly |
| **Fail closed** | Post-call guardrail, egress classification | An undecidable classification blocks; it does not pass |
| **Defence in depth** | Injection resistance | Envelope + detection classifier + unregisterable scopes + no customer channel. No single control is load-bearing |
| **Least privilege with workload identity** | Every component | NFR-037, NFR-038. No static credentials anywhere |
| **Row-level security** | Jurisdiction isolation | ADR-014. Enforcement below the application, so an application bug is not a breach |
| **Append-only audit** | `audit_event` | Application role holds INSERT only; UPDATE and DELETE revoked at the database |
| **Content addressing** | Evidence | Tamper-evidence by construction |

---

## 5. Data patterns

| Pattern | Applied to | Why |
|---|---|---|
| **Associative entity** | `case_alert`, `finding_evidence`, `party_account_role`, `alert_transaction` | The relationships carry attributes (stance, reason, linked/unlinked timestamps). They are entities, not join tables |
| **Temporal validity** | `party_relationship`, `party_account_role`, `policy_version`, rule catalogue | Point-in-time reconstruction (NFR-031) requires knowing what was true then, not what is true now |
| **Slowly changing dimension (type 2)** | Party and account attributes | A disposition must be explicable against the KYC record of the day |
| **Soft supersession, never update** | `decision`, `report_version`, `evidence_item` | Supersede with a link; both records remain readable |
| **Declarative partitioning** | `ai_run`, `model_call`, `audit_event`, `transaction` | Monthly range partitions so expiry is a partition drop, not a mass delete (NFR-015) |
| **Natural key preserved alongside surrogate** | All source-derived entities | `external_reference` keeps the source identifier so reconciliation with Actimize is possible |

---

## 6. Patterns in the agent itself

| Pattern | Description |
|---|---|
| **Verify-then-trust loop** | Act, verify deterministically, escalate on failure, bounded attempts. The verification is independent of the actor, which is what distinguishes it from self-critique |
| **Evidence gate** | Groundedness as a routing signal rather than only a quality metric (ADR-003) |
| **Safe degradation** | `insufficient_information` is a first-class output, not an error. BR-016 |
| **Recommendation / authority split** | The agent writes a recommendation; only an `actor` writes a `decision`. Enforced by separate tables and separate permissions |
| **Deterministic grader** | Groundedness, threshold checks and control outcomes are pure functions with unit tests (ADR-004) |

---

## 7. Patterns considered and rejected

| Pattern | Rejected because |
|---|---|
| **Microservices per domain** | Six services sharing one tightly-coupled transactional model would trade a tractable monolith for distributed transactions. A modular monolith with clear ports gives the same boundaries without the consistency problem. Revisit only if team topology demands it |
| **Event sourcing throughout** | Reconstructability is required for decisions and audit, which §2.6 provides. Full event sourcing would impose projection complexity on alerts and transactions that gain nothing from it |
| **LLM-as-judge for grounding** | ADR-004 |
| **Graph database as system of record** | ADR-012. Relationships are modelled relationally; a projection serves network analysis without a second source of truth |
| **Vector retrieval over transactions** | ADR-015. Approximate match on evidence is unacceptable |
| **Feature flags for model and prompt** | ADR-009. A runtime toggle on model behaviour is an unvalidated model change |
| **Multi-agent debate / self-consistency ensembles** | Cost multiplies with no measured recall benefit on this corpus; it also defeats reconstructability. Revisit only with evidence from the evaluation harness |
| **Caching of completions** | Two alerts are rarely identical, and a cache hit on a changed rule version would silently serve a stale interpretation. Prompt-prefix caching is a separate, bounded question tracked in AMLI-PLAN-001 Phase 4 |
