# Functional Requirements Specification

| | |
|---|---|
| **Document ID** | AMLI-FRS-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Business Analyst |
| **Approver** | Head of Financial Crime Technology |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. How to read this document

Requirements are grouped by functional area and numbered permanently. Each
carries a MoSCoW priority, the business requirement it serves, and at least one
testable acceptance criterion. Traceability to components, APIs and test cases
is maintained in AMLI-RTM-001.

| Area | Range | Component |
|---|---|---|
| A — Ingestion and normalisation | FR-001 … FR-012 | `ingest` |
| B — Rule catalogue and retrieval | FR-013 … FR-020 | `rules` |
| C — Evidence capture | FR-021 … FR-030 | `evidence` |
| D — Agent runtime | FR-031 … FR-044 | `agent` |
| E — Findings and disposition | FR-045 … FR-053 | `agent`, `case` |
| F — Case and consolidation | FR-054 … FR-060 | `case` |
| G — Human review and decision | FR-061 … FR-068 | `review` |
| H — Reporting support | FR-069 … FR-072 | `report` |
| I — Write-back | FR-073 … FR-076 | `integration` |
| J — Evaluation and improvement | FR-077 … FR-086 | `improve` |
| K — Security and control | FR-087 … FR-094 | `security` |
| L — Administration and configuration | FR-095 … FR-101 | `admin` |

---

## 2. Area A — Ingestion and normalisation

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-001 | The system shall ingest alerts from Actimize SAM via the integration adapter defined in AMLI-INT-001 | M | BR-001 | An alert present in SAM appears in `alert` within the agreed ingestion window; field mapping matches AMLI-INT-001 §4 |
| FR-002 | The system shall support two ingestion modes — API pull and scheduled file extract — selectable per environment without code change | M | BR-001 | Both modes pass the same contract test suite; switching is a configuration change only |
| FR-003 | The system shall ingest the party, account and transaction records referenced by an alert | M | BR-001 | For every ingested alert, all referenced parties, accounts and transactions resolve; unresolved references raise a data-quality exception, not a silent drop |
| FR-004 | The system shall record, for every ingested record, its source system, source identifier and ingestion timestamp | M | BR-010 | `source_system` and `external_reference` populated on 100% of ingested rows |
| FR-005 | The system shall be idempotent on re-ingestion of the same source record | M | BR-010 | Re-running an extract produces no duplicate alerts and no changed `alert_id` |
| FR-006 | The system shall detect and reject records that fail schema or referential validation, and quarantine them with a reason | M | BR-010 | Invalid record appears in the quarantine queue with a machine-readable reason code; no partial write to the main tables |
| FR-007 | The system shall capture the detection version (scenario, rule or model version, effective dates) that raised each alert | M | BR-005 | `alert.detection_version_id` resolves for 100% of alerts |
| FR-008 | The system shall capture the actual values text the detection engine recorded when the alert fired | M | BR-002 | `alert.triggered` populated where supplied by source |
| FR-009 | The system shall normalise transaction direction, medium, currency and country to a controlled vocabulary | M | BR-001 | Values outside the vocabulary are quarantined under FR-006 |
| FR-010 | The system shall preserve payment reference and remittance free text verbatim and flag it as untrusted at ingestion | M | BR-011 | `transaction.reference_text` is byte-identical to source; `is_untrusted` set true |
| FR-011 | The system shall tag every ingested record with the institution and jurisdiction it belongs to | M | BR-012 | Row-level security policy (AMLI-DDL-001 §9) rejects cross-jurisdiction reads in test |
| FR-012 | The system shall support replay of ingestion for a stated date range without duplicating downstream investigations | S | BR-010 | Replay of a processed day creates no new `ai_run` records unless explicitly requested |

---

## 3. Area B — Rule catalogue and retrieval

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-013 | The system shall maintain a versioned catalogue of detection rule specifications, each traceable to its source document and page | M | BR-005 | Every catalogue entry carries `source_document`, `source_page`, `rule_id`, `version`, `effective_from` |
| FR-014 | The catalogue shall be populated by extraction from the source specification, not by manual transcription into prompts | M | BR-005 | Extraction job is reproducible; a diff against the prior version is produced on every rebuild |
| FR-015 | The system shall retrieve the rule applicable to an alert by scenario code and the alert's effective date | M | BR-005 | Given a scenario and a date, the retrieved rule is the one in force on that date |
| FR-016 | The retrieved rule, its thresholds and its source citation shall be supplied to the agent as part of the investigation context | M | BR-002, BR-005 | Rule text and page citation appear verbatim in the captured prompt |
| FR-017 | The system shall refuse to investigate an alert whose scenario has no catalogue entry | M | BR-016 | Disposition `insufficient_information` with reason `no_rule_for_scenario`; no model call is made |
| FR-018 | The system shall support institution-specific threshold overrides, recorded separately from the vendor defaults | S | BR-005 | Override is visible in the retrieved rule with both the default and the override value |
| FR-019 | A change to the catalogue shall be versioned, approved and effective-dated, never applied retrospectively | M | BR-014 | Historic runs continue to resolve the catalogue version in force at the time |
| FR-020 | The system shall expose which catalogue version was used by any given run | M | BR-010 | `ai_run.rule_catalogue_version` populated and queryable |

---

## 4. Area C — Evidence capture

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-021 | The system shall create an immutable evidence item for every data source consulted during an investigation | M | BR-006 | One `evidence_item` row per consulted source, linked to the run |
| FR-022 | Each evidence item shall record source reference, capture timestamp, content hash and a protected snapshot location | M | BR-006 | All four fields non-null; hash verifies against the stored object |
| FR-023 | A live reference without a captured snapshot shall not be accepted as evidence | M | BR-006 | Attempt to create an evidence item without `storage_uri` is rejected |
| FR-024 | Evidence snapshots shall be stored in object storage with write-once semantics for the retention period | M | BR-006 | Object lock verified in a control test; delete attempt fails |
| FR-025 | Evidence access shall be recorded with the purpose of access | M | BR-010 | `run_evidence.access_purpose` populated on every access |
| FR-026 | The system shall make evidence available to a reviewer exactly as the agent saw it | M | BR-006 | Reviewer view is rendered from the snapshot, not re-queried from source |
| FR-027 | The system shall apply retention and legal-hold policy to evidence objects | M | BR-010 | An item under legal hold is not expired by the retention job |
| FR-028 | The system shall deduplicate identical evidence by content hash within an investigation | S | BR-006 | Two accesses to unchanged source produce one evidence item and two access records |
| FR-029 | The system shall detect and record when source data has changed since capture | S | BR-006 | On re-access, a differing hash creates a new evidence item and flags supersession |
| FR-030 | Evidence shall be classified for sensitivity and PII content at capture | M | BR-012 | Classification present on 100% of items; drives masking under FR-092 |

---

## 5. Area D — Agent runtime

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-031 | The system shall execute one agent run per alert or case investigation and create an `ai_run` record for it | M | BR-010 | Every investigation has exactly one run; run carries deployment, case, trace identifiers |
| FR-032 | Every model call, tool call, control check and evidence access shall be linked to its run | M | BR-010 | No orphan `model_call`, `tool_call`, `control_check` or `run_evidence` rows exist |
| FR-033 | The system shall render an alert for the model without its label, adjudication or outcome | M | BR-013 | Rendered prompt contains none of the label fields; verified by a test asserting absence |
| FR-034 | The system shall route each run to the least costly serving model that meets the configured quality floor | M | BR-009 | Routing decision and chosen model recorded on the run |
| FR-035 | The system shall escalate a run to a higher-capability model when the answer cites no evidence, or cites a reference absent from the captured evidence | M | BR-002, BR-016 | Evidence-gate trigger and the escalation are recorded as separate attempts on the run |
| FR-036 | The number of escalations per run shall be bounded by configuration | M | BR-009 | Exceeding the bound yields `insufficient_information`, not an unbounded spend |
| FR-037 | The system shall enforce a per-run and per-period spend cap | M | BR-009 | Exceeding the cap aborts the run with reason `budget_exceeded` and raises an alert |
| FR-038 | The system shall fall back to an alternative provider or model on provider failure | M | BR-016 | Simulated provider error produces a successful run via fallback, recorded as such |
| FR-039 | All model calls shall pass through a single provider abstraction | M | BR-010 | No component other than the LLM gateway opens a provider connection; enforced by architecture test |
| FR-040 | Tool invocations shall be idempotent and carry an idempotency key | M | BR-010 | Replaying a tool call with the same key produces no duplicate effect |
| FR-041 | The agent shall have no tool capable of closing an alert, deciding a case, writing to a party record, releasing a payment, or submitting a report | M | BR-003 | Such scopes are not merely ungranted but unregisterable; attempting to register one raises an error at start-up |
| FR-042 | The system shall capture the exact system prompt, user prompt, model identifier and parameters used for every call | M | BR-010 | Captured content hashes match what was sent; replay reproduces the call |
| FR-043 | The system shall time-bound every model call and tool call, and treat a timeout as a failure, not an empty answer | M | BR-016 | Timeout produces an attempt with status `timeout`; no disposition is derived from it |
| FR-044 | The system shall support running a challenger model alongside the champion without affecting the production disposition | S | BR-013 | Challenger results stored, excluded from the disposition path |

---

## 6. Area E — Findings and disposition

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-045 | The system shall parse the model response into a structured verdict comprising disposition, reasoning and citations | M | BR-001 | Unparseable response yields `unparseable` status, never a guessed disposition |
| FR-046 | The system shall produce exactly one of three dispositions: `close_no_further_action`, `escalate_to_case`, `insufficient_information` | M | BR-001 | Any other value is rejected at parse |
| FR-047 | The system shall create a finding for each distinct assertion the agent makes | M | BR-002 | Findings are individually addressable and reviewable |
| FR-048 | Each finding shall link to the evidence it relies on, with a stance of `supports` or `contradicts` | M | BR-002 | `finding_evidence.stance` populated for every link |
| FR-049 | The system shall compute groundedness deterministically by resolving each citation against the captured evidence | M | BR-002 | No second model is involved; the check is a pure function with unit tests |
| FR-050 | A finding that cites a reference not present in the evidence shall be marked ungrounded and shall not support a disposition | M | BR-002, BR-016 | Ungrounded finding cannot be the sole basis of an escalation recommendation |
| FR-051 | The system shall record a confidence value for each recommendation, calibrated and monitored | S | BR-013 | Calibration curve produced monthly per AMLI-MRM-001 §6 |
| FR-052 | The recommendation shall be stored as a recommendation, distinct from any decision | M | BR-003, BR-007 | Recommendation and decision are separate records with separate actors |
| FR-053 | Where the agent cannot ground an answer, it shall return `insufficient_information` with the reason, rather than a low-confidence disposition | M | BR-016 | Reason code present and enumerated |

---

## 7. Area F — Case and consolidation

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-054 | The system shall represent a case as an entity distinct from an alert, with a many-to-many relationship between them | M | BR-008 | A case may hold several alerts; an alert may be linked to a case and later unlinked |
| FR-055 | The system shall preserve link and unlink history with timestamp, actor and reason | M | BR-008, BR-010 | `case_alert.linked_at`, `unlinked_at`, `reason`, `actor_id` populated |
| FR-056 | The system shall propose consolidation of alerts sharing a party, account or typology within a configurable window | S | BR-008 | Proposal surfaced to the reviewer; never applied automatically |
| FR-057 | Consolidation shall require human confirmation | M | BR-003 | No `case_alert` row is created by the agent without a decision record |
| FR-058 | The system shall support investigation plans composed of tasks, derived from policy | S | BR-001 | Plan and tasks created per case; task status tracked |
| FR-059 | The system shall link the policy version in force to each investigation plan | M | BR-010 | `investigation_plan.policy_version_id` populated |
| FR-060 | The system shall record case status transitions with actor and timestamp | M | BR-010 | Status history queryable; no transition without an actor |

---

## 8. Area G — Human review and decision

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-061 | The system shall present the recommendation, the reasoning, the findings and the evidence to an authorised reviewer | M | BR-001 | Reviewer workspace renders all four from stored records |
| FR-062 | The reviewer shall be able to accept, override or request more information | M | BR-003, BR-007 | Three outcomes available; each creates a decision record |
| FR-063 | Every decision shall record the deciding actor, timestamp, outcome and rationale | M | BR-007 | All four non-null on 100% of decisions |
| FR-064 | An override shall capture the reviewer's reason in structured form | M | BR-013 | Reason selected from a controlled list plus free text; feeds failure mining under FR-079 |
| FR-065 | The system shall record whether the decision agreed with the recommendation | M | BR-007 | `decision.agreed_with_recommendation` derived and stored |
| FR-066 | A decision may supersede an earlier decision on the same case, preserving both | M | BR-010 | `decision.supersedes` populated; the superseded record remains readable |
| FR-067 | Escalation to a case shall require a decision by an actor holding the escalation permission | M | BR-003 | Permission check enforced server-side, not only in the interface |
| FR-068 | The system shall be capable of reporting, at any time, the number of dispositions taken without a human decision — which shall be zero | M | BR-003 | Control report returns zero; a non-zero result is a P1 incident |

---

## 9. Area H — Reporting support

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-069 | The system shall draft a report narrative from approved findings on request | S | BR-015 | Draft contains only content traceable to findings marked grounded |
| FR-070 | A draft narrative shall be versioned, with the generating run recorded | M | BR-010 | `report_version.generated_by_run_id` populated |
| FR-071 | The system shall not submit a report to any external authority under any circumstances | M | BR-003 | No submission capability exists in the codebase; verified by the scope test in FR-041 |
| FR-072 | Approval of a report version shall require an authorised human actor and shall be recorded | M | BR-003 | Approval record with actor, timestamp and version hash |

---

## 10. Area I — Write-back to the Actimize estate

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-073 | The system shall write the recommendation and its evidence pack back to the corresponding case record in ActOne | M | BR-001 | Write-back appears on the case; content matches the stored recommendation |
| FR-074 | Write-back shall be idempotent and retried safely on failure | M | BR-010 | Duplicate delivery produces one case note; verified with an idempotency key test |
| FR-075 | Write-back shall never alter alert or case status in the source system | M | BR-003 | Adapter has no status-mutation capability; contract test asserts the absence |
| FR-076 | Failure to write back shall be visible, retriable and shall not lose the recommendation | M | BR-016 | Failed deliveries appear in an operator queue with full payload retained |

---

## 11. Area J — Evaluation and improvement

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-077 | The system shall maintain a versioned evaluation dataset with adjudicated labels and recorded label confidence | M | BR-017 | Dataset version is immutable; items carry `label`, `label_basis`, `label_confidence` |
| FR-078 | The system shall store outcome, adjudication and label separately and shall not derive a suspicion label from a filing alone | M | BR-017 | A CTR-only outcome does not produce a positive suspicion label |
| FR-079 | The system shall cluster failures and human overrides by features observable in the alert, never by the label | M | BR-013 | Clustering inputs exclude label fields; enforced by test |
| FR-080 | The system shall generate improvement proposals carrying the evidence that produced them | M | BR-013 | Proposal links to the cluster and the affected runs |
| FR-081 | Every proposal shall be evaluated against the same dataset and baseline using a paired statistical test | M | BR-014 | Evaluation result records effect size, significance and the test used |
| FR-082 | A proposal that reduces recall below the floor shall be refused regardless of its cost benefit | M | BR-014 | Gate refuses; refusal and reason are recorded |
| FR-083 | Approved changes shall produce a new asset version and a release, and shall not take effect without deployment | M | BR-014 | Change approval links evaluation run, candidate release and approver |
| FR-084 | The system shall support rollback to any previously deployed release | M | BR-014 | Rollback exercised in each release rehearsal |
| FR-085 | The system shall monitor for drift in input distribution and in output distribution, and raise a deviation when either exceeds its band | M | BR-013 | Deviation raised with the band and the standard-error basis |
| FR-086 | The system shall compute cost per alert, per case and per outcome continuously | M | BR-009 | Figures reconcile to the ledger; no value is computed in two places |

---

## 12. Area K — Security and control

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-087 | All data the agent reads that originates outside the institution shall be enclosed in an untrusted-data envelope | M | BR-011 | Envelope present in the captured prompt; verified per run |
| FR-088 | The system shall run control checks before tool access and before output emission, recording allow, block or escalate | M | BR-010 | `control_check` row per evaluation with policy version |
| FR-089 | The system shall detect and record prompt-injection attempts as security events linked to the run | M | BR-011 | Known payload corpus produces a security event in every case |
| FR-090 | Output destined for any customer-visible channel shall be blocked at the emission boundary | M | BR-004 | No such channel is configured; attempted emission raises a security event and fails closed |
| FR-091 | Telemetry, logs and metrics shall carry no customer identifiers or transaction content | M | BR-012 | Automated scan of log output finds no PII patterns |
| FR-092 | Non-production environments shall use synthetic or masked data only | M | BR-012 | Data-provisioning job enforces masking; attested per environment refresh |
| FR-093 | The system shall maintain an append-only audit event stream that cannot be modified by the application | M | BR-010 | Application role has insert-only grant; update and delete revoked |
| FR-094 | The system shall be subjected to an automated adversarial probe suite on every release candidate | M | BR-018 | Suite runs in the pipeline; a new exploit blocks the release |

---

## 13. Area L — Administration and configuration

| ID | Requirement | Pri | BR | Acceptance criteria |
|---|---|---|---|---|
| FR-095 | The system shall expose agent configuration as versioned, approved assets, not as editable runtime settings | M | BR-014 | Configuration change requires an asset version and a release |
| FR-096 | The system shall support institution and jurisdiction scoping of all configuration | M | BR-012 | Two tenants with different thresholds operate concurrently in test |
| FR-097 | Role-based access control shall govern every function, enforced server-side | M | BR-003 | Permission matrix in AMLI-SEC-001 §7 tested per role |
| FR-098 | The system shall provide an operator view of queue depth, failures and quarantined records | M | BR-016 | Operator console surfaces all three |
| FR-099 | The system shall allow an authorised operator to pause and resume processing without data loss | M | BR-016 | Pause drains in flight work; resume processes the backlog |
| FR-100 | The system shall record every configuration change with actor, timestamp, before and after values | M | BR-010 | Change history queryable and immutable |
| FR-101 | The system shall provide a model inventory export suitable for the institution's MRM register | S | BR-014 | Export matches the fields required by AMLI-MRM-001 §2 |

---

## 14. Requirement summary

| Priority | Count |
|---|---|
| Must | 86 |
| Should | 15 |
| Could | 0 |
| Won't (this release) | 0 |
| **Total** | **101** |

Scope control note: the high proportion of *Must* reflects a regulated control
rather than optimistic scoping. Where a requirement could be deferred it has
been marked *Should*; where it cannot, deferring it would make the system
unapprovable rather than merely less capable.
