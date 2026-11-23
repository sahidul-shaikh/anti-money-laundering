# RAID Log — Risks, Assumptions, Issues, Dependencies

| | |
|---|---|
| **Document ID** | AMLI-RAID-001 |
| **Version** | 0.1 |
| **Status** | Draft — live document |
| **Owner** | Delivery Lead |
| **Review cadence** | Weekly at the delivery forum; monthly at the steering group |
| **Date** | 18 November 2026 |

Scoring: Probability and Impact 1 (low) to 5 (high). Exposure = P × I. Anything
at 15 or above is reported to the steering group every month until mitigated.

---

## 1. Risks

| ID | Risk | P | I | Exp | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| **RISK-001** | **No adjudicated label set is funded or delivered, so no defensible accuracy claim can be made and MRM cannot validate** | 4 | 5 | **20** | Scope the adjudication exercise into Phase 1 with named investigator time; present the label-contamination analysis to the sponsor early so the need is understood before it becomes a blocker; interim reporting qualified and bounded | Model Risk Lead | **Open — highest exposure** |
| **RISK-002** | Investigators do not adopt a recommendation-first workflow and continue investigating from scratch, so handling time does not fall and the business case fails | 3 | 5 | 15 | Involve L1 analysts in design from Phase 1; measure handling time from day one; make evidence reachable in one interaction; treat override reasons as product feedback, not noise | Investigations Manager | Open |
| **RISK-003** | Recall cannot be demonstrated at 0.90 on adjudicated labels | 3 | 5 | 15 | Evidence gate and escalation already target the failure mode; challenger comparison in Phase 3; if unachievable, narrow scope to the scenarios where it is, rather than lowering the floor | Model Risk Lead | Open |
| **RISK-004** | Actimize API access is not granted, forcing file extract and losing near-real-time triage | 3 | 3 | 9 | Both ingestion modes designed and contract-tested from Phase 1; extract mode is a supported path, not a degradation | Integration Architect | Open |
| **RISK-005** | A successful prompt-injection technique emerges that the envelope does not resist | 2 | 5 | 10 | Four-layer defence; capability layer does not depend on model behaviour; adversarial suite on every release; external pentest | Security Architect | Open |
| **RISK-006** | Bedrock throughput quota becomes the binding constraint at peak volume | 3 | 3 | 9 | Quota tracked as a supplier dependency; increases requested ahead of volume; batch window widened as a fallback; second provider spike before go-live | SRE Lead | Open |
| **RISK-007** | Provider changes a pinned model version or deprecates it, invalidating validation | 3 | 4 | 12 | Versions pinned; deprecation notices monitored; fallback tier maintained and validated; a version change is a release with full re-validation | SRE Lead | Open |
| **RISK-008** | Customer PII leaks into telemetry or a non-production environment | 2 | 5 | 10 | Field allow-list in logging; automated PII scan blocking the build; masked provisioning; quarterly access review | Security Architect | Open |
| **RISK-009** | State divergence between our record and ActOne confuses investigators or auditors | 3 | 3 | 9 | Daily reconciliation report; divergence above threshold is a P2; ActOne remains authoritative by design | Integration Architect | Open |
| **RISK-010** | Evidence storage growth and cost exceed forecast | 2 | 2 | 4 | Deduplication by content hash; lifecycle to colder storage after 90 days; monthly cost review | SRE Lead | Open |
| **RISK-011** | Fairness testing reveals differential behaviour by nationality, age or occupation | 2 | 5 | 10 | Testing designed in from Phase 2 rather than retrofitted; a finding is reported to Compliance, not tuned away; attribute ablation available as a remedy with its quality cost measured | Model Risk Lead | Open |
| **RISK-012** | The 13-entity core proves insufficient and forces schema rework | 2 | 3 | 6 | Extension points documented in AMLI-DM-001 §7; the reference model was designed before the subset was chosen | Data Architect | Open |
| **RISK-013** | Key-person dependency on the small group who understand the agent runtime | 3 | 3 | 9 | Pair work mandated; design documents maintained as the source of truth; runbooks rehearsed by people who did not write them | Delivery Lead | Open |
| **RISK-014** | MRM validation takes longer than planned and delays go-live | 3 | 4 | 12 | Validator engaged from Phase 1, not at the end; V-1 to V-10 staged across phases rather than batched; validation evidence produced continuously by the harness | Model Risk Lead | Open |
| **RISK-015** | EU AI Act or local classification changes the obligations mid-build | 2 | 4 | 8 | Human decision on every disposition is already the strongest mitigation; Legal review per jurisdiction before rollout (DEP-007) | Compliance | Open |
| **RISK-016** | Scope expands to further typologies before the first is validated | 3 | 3 | 9 | Phase exit criteria are explicit; new typologies require their own adjudicated sample and validation | Delivery Lead | Open |

### Risk heat

| Exposure | Count | IDs |
|---|---|---|
| 15–25 | 3 | RISK-001, RISK-002, RISK-003 |
| 10–14 | 4 | RISK-005, RISK-007, RISK-008, RISK-011, RISK-014 |
| < 10 | 9 | the remainder |

**RISK-001 is the one to act on first.** Everything the programme claims about
quality depends on labels that do not yet exist, and the exercise needs
investigator time that has to be funded and scheduled, not assumed.

---

## 2. Assumptions

| ID | Assumption | Validated by | If false |
|---|---|---|---|
| ASM-001 | Actimize exposes alerts, parties, accounts and transactions via API or scheduled extract | Phase 0 technical discovery | Ingestion redesign; Phase 1 slips 4–6 weeks |
| ASM-002 | The client funds an adjudicated label set of ≥ 1,000 alerts | Sponsor decision, Phase 0 | O-2 unmeasurable; MRM cannot validate; **programme cannot reach production** |
| ASM-003 | Bedrock is approved for customer data in the client's region | Phase 0 security review | LLM layer re-points; ADR-002 superseded; 3–4 weeks |
| ASM-004 | Counterparty data is obtainable for the network scenarios | Phase 2 discovery | SAS10602 and SAS10012 leave scope |
| ASM-005 | L1 analysts will work from a recommendation | Phase 2 UAT | Business case at risk; see RISK-002 |
| ASM-006 | The Solution Guide may be used as the threshold source under the vendor agreement | Legal review, Phase 0 | Thresholds re-sourced from the deployed configuration; 2 weeks |
| ASM-007 | Seven-year retention is the applicable obligation in every target jurisdiction | Legal review per jurisdiction | Retention policy per jurisdiction; schema already supports it |
| ASM-008 | 12,000 alerts/day steady state and 40,000 peak are representative | Phase 0 volume analysis | Capacity model recalculated; §1 of AMLI-NFR-001 is the single point of change |
| ASM-009 | Investigator time is available for UAT and adjudication without backfill | Resource plan | Both activities slip; see RISK-001, RISK-002 |
| ASM-010 | The institution's IdP supports the required groups and MFA | Phase 0 | Access model simplified; compensating controls recorded |

---

## 3. Issues

Open items that are already true, not risks of becoming true.

| ID | Issue | Impact | Action | Owner | Target |
|---|---|---|---|---|---|
| **ISS-001** | `PRD.md` §5.2 states a human reviews every escalation **and every close**, while the current reference implementation reviews only escalations. The two cannot both be true, and the saving case depends on which | Business case and control claim both affected | Sponsor decision required before Phase 1 exit. Note that reviewing every close removes most of the saving; reviewing none is a real control weakening | Product Owner | Phase 1 |
| ISS-002 | No adjudicated labels exist today | No defensible accuracy claim | See RISK-001 | Model Risk Lead | Phase 1 |
| ISS-003 | Counterparty data absent from the available extract | Two in-scope scenarios cannot be built | Deferred to Phase 4; DEP-004 raised | Data Architect | Phase 2 |
| ISS-004 | The reference implementation ties `run_id` to model calls only, not to security or evaluation records | ADR-008 not yet fully realised | Explicit Phase 2 scope | Engineering Lead | Phase 2 |
| ISS-005 | FR-044 and FR-101 have no test defined | Traceability gap | Tests designed in Phase 3 when the capabilities exist | Test Lead | Phase 3 |
| ISS-006 | NFR-079 licence scanning not wired into the pipeline | Compliance gap | Phase 1 pipeline work | Engineering Lead | Phase 1 |
| ISS-007 | Schema has not been applied to a live PostgreSQL instance; only syntax-checked | DDL defects possible | Phase 0 task: apply to a real instance, run the constraint test suite | Data Architect | Phase 0 |

---

## 4. Dependencies

| ID | Dependency | On whom | Needed by | Status |
|---|---|---|---|---|
| DEP-001 | Actimize API credentials and a non-production endpoint | Client Actimize team | Phase 0 end | Not started |
| DEP-002 | AWS accounts, network connectivity, Bedrock model access | Client cloud platform team | Phase 0 end | Not started |
| DEP-003 | Investigator time for adjudication (≈ 25 person-days) | Investigations Manager | Phase 1 start | **Not secured — see RISK-001** |
| DEP-004 | Counterparty and party-relationship data source | Client data team | Phase 3 start | Not started |
| DEP-005 | IdP group provisioning for the seven roles | Client identity team | Phase 1 end | Not started |
| DEP-006 | MRM validator assignment and engagement | Model Risk Management | Phase 1 start | Not started |
| DEP-007 | Legal opinion on automated decision-making per jurisdiction | Legal | Before each rollout | Not started |
| DEP-008 | DPO approval of the field-level rendering policy | Data Protection Officer | Phase 1 end | Not started |
| DEP-009 | Penetration test slot | Security / external supplier | Before go-live | Not started |
| DEP-010 | ActOne note-write service account | Client Actimize team | Phase 2 end | Not started |
| DEP-011 | Masked data provisioning pipeline for UAT | Client data team | Phase 2 start | Not started |
| DEP-012 | Bedrock quota increase for peak volume | AWS | Before production volume | Not started |
| DEP-013 | Source-of-truth decision per artifact, and linkage to the client's requirements and change tools | Client engineering governance | Phase 0 end | Not started |

### Critical path

`DEP-002` → `DEP-001` → Phase 1 build; and in parallel `DEP-003` → adjudication
→ `DEP-006` → MRM validation → go-live.

**The label path, not the build path, is the longer one.** Adjudication takes
calendar time that cannot be compressed by adding engineers, and validation
cannot start without it. It should be started in Phase 0, before the build is
finished, not after.
