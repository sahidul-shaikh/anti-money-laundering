# AML Alert Investigator — Solution Design Documentation

Design documentation set for the AML Alert Investigator, produced to the standard
a regulated financial-crime change programme would require.

| | |
|---|---|
| **Programme** | AI for AI — Financial Crime |
| **Product** | AML Alert Investigator (AMLI) |
| **Document ID** | AMLI-IDX-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Date** | 18 November 2026 |
| **Classification** | Internal — Accenture / Client Confidential |
| **Owner** | Solution Architect |
| **Approver** | Head of Financial Crime Technology |

---

## 1. What this set describes

The **target production system**: the AML Alert Investigator as it would be built
for a bank and run in production — multi-user, multi-jurisdiction, integrated
with the incumbent alert and case management estate (NICE Actimize), and
governed to model-risk standard.

It is not documentation of the demonstration console. Where the existing
reference implementation in `aml/` validates a design decision, it is cited as
evidence, and the delivery plan (AMLI-PLAN-001) states explicitly what is
already proven and what is still to be built.

### Design baseline

Three inputs are carried into this design and should be read alongside it:

| Input | What it contributes |
|---|---|
| `PRD.md` | The original product requirements, commercial targets and constraints |
| `decks/AI_for_AI_AML.pptx` | The reference logical data model (three domains, `AI_RUN` as integration point) and the seven design constraints adopted in AMLI-DM-001 |
| `Anthropic_AI_SDLC_Guide.pdf` | The AI-native SDLC practices adopted for how the programme itself runs — see AMLI-SDLC-001 |
| `aml/` reference implementation | Working proof of the agent runtime, evidence gating, adversarial defence and the improvement loop |

### Decisions taken before drafting

| Decision | Choice | Recorded in |
|---|---|---|
| Scope | Target production system for a bank | AMLI-BRD-001 §3 |
| Data model depth | Core 13 entities implemented; full reference model as target schema | ADR-008, AMLI-DM-001 |
| Platform | AWS-native (Bedrock, Aurora PostgreSQL, S3, OpenSearch) | ADR-002, ADR-012 |
| Integration posture | Read from Actimize, write recommendation back; SAM remains authoritative | ADR-013, AMLI-INT-001 |

---

## 2. Document index

### 00 — Programme foundation

| # | Document | ID | Purpose |
|---|---|---|---|
| 00 | [Glossary and abbreviations](00-glossary.md) | AMLI-GLO-001 | Financial-crime and engineering vocabulary used throughout |

### 01 — Requirements

| # | Document | ID | Purpose |
|---|---|---|---|
| 01 | [Business requirements](01-business-requirements.md) | AMLI-BRD-001 | Problem, drivers, objectives, scope, value contract, regulatory context |
| 02 | [Functional requirements](02-functional-requirements.md) | AMLI-FRS-001 | FR-001 … FR-078, with acceptance criteria |
| 03 | [Non-functional requirements](03-non-functional-requirements.md) | AMLI-NFR-001 | NFR-001 … NFR-061, each with a measurable target |
| 04 | [Use cases and user stories](04-use-cases-and-user-stories.md) | AMLI-UC-001 | UC-01 … UC-14, actors, flows, exceptions |

### 02 — Architecture

| # | Document | ID | Purpose |
|---|---|---|---|
| 05 | [High-level design](05-high-level-design.md) | AMLI-HLD-001 | Principles, context / container / component / deployment views, capacity model |
| 06 | [Architecture decision records](06-architecture-decision-records.md) | AMLI-ADR-001 | ADR-001 … ADR-018, each with context, decision, consequences |
| 07 | [Data flow diagrams](07-data-flow-diagrams.md) | AMLI-DFD-001 | DFD levels 0–2, trust boundaries, data classification per flow |
| 08 | [Design patterns](08-design-patterns.md) | AMLI-PAT-001 | Pattern register — what is used, where, and why |

### 03 — Detailed design

| # | Document | ID | Purpose |
|---|---|---|---|
| 09 | [Low-level design](09-low-level-design.md) | AMLI-LLD-001 | Module decomposition, interfaces, state machines, sequence diagrams, error handling |

### 04 — Data

| # | Document | ID | Purpose |
|---|---|---|---|
| 10 | [Logical data model](10-data-model.md) | AMLI-DM-001 | Three domains, ERDs, entity definitions, relationship and labelling rules |
| 11 | [Physical database schema](11-database-schema.sql) | AMLI-DDL-001 | PostgreSQL DDL — tables, keys, indexes, constraints, partitioning, RLS |
| 12 | [Data dictionary](12-data-dictionary.md) | AMLI-DD-001 | Column-level definitions with PII classification, source and retention |

### 05 — Interfaces

| # | Document | ID | Purpose |
|---|---|---|---|
| 13 | [API specification](13-api-specification.md) | AMLI-API-001 | REST resources, auth, idempotency, errors, examples |
| 14 | [OpenAPI contract](14-openapi.yaml) | AMLI-API-002 | Machine-readable OpenAPI 3.1 definition |
| 15 | [Integration design](15-integration-design.md) | AMLI-INT-001 | Actimize SAM / ActOne adapters, ingestion modes, field mappings, replay |

### 06 — Security, risk and quality

| # | Document | ID | Purpose |
|---|---|---|---|
| 16 | [Security design](16-security-design.md) | AMLI-SEC-001 | STRIDE and LINDDUN analysis, prompt-injection threat model, controls |
| 17 | [Model risk and validation](17-model-risk-and-validation.md) | AMLI-MRM-001 | SR 11-7 aligned validation plan, label integrity, monitoring, challenger |
| 18 | [Test strategy](18-test-strategy.md) | AMLI-TST-001 | Test pyramid, golden corpus, adversarial suite, evaluation gates |
| 19 | [Observability and SLOs](19-observability-and-slos.md) | AMLI-OBS-001 | Five-layer telemetry, metric catalogue, SLIs/SLOs, alerting |

### 07 — Delivery and operations

| # | Document | ID | Purpose |
|---|---|---|---|
| 20 | [Deployment and operations](20-deployment-and-operations.md) | AMLI-OPS-001 | Environments, IaC, CI/CD, release and rollback, BCDR, cost control |
| 21 | [Requirements traceability matrix](21-traceability-matrix.md) | AMLI-RTM-001 | BR → FR/NFR → component → API → test → ADR |
| 22 | [RAID log](22-raid-log.md) | AMLI-RAID-001 | Risks, assumptions, issues, dependencies |
| 23 | [Delivery plan](23-delivery-plan.md) | AMLI-PLAN-001 | Phases, workstreams, team shape, estimates, milestones, exit criteria |
| 24 | [AI-native SDLC method](24-ai-native-sdlc-method.md) | AMLI-SDLC-001 | How the programme itself runs: artifact chain, skill/hook controls, agent evals, programme indicators |

---

## 3. Reading order by role

| Role | Read |
|---|---|
| **Sponsor / Head of FinCrime Technology** | 01, 23, 22, then 17 |
| **Solution architect** | 05, 06, 10, 07, 08, then 09 |
| **Engineering lead** | 09, 11, 13, 15, 20, 24 |
| **Data architect** | 10, 11, 12, 07 |
| **Security architect** | 16, 07 §4, 06 (ADR-005, ADR-006, ADR-014) |
| **Model risk / validation** | 17, 18, 10 §6 (labelling), 19 |
| **Test lead** | 18, 02, 03, 21 |
| **Operations / SRE** | 20, 19, 03 §2–§4 |
| **Business analyst** | 01, 02, 04, 21 |

---

## 4. Document conventions

**Identifiers.** Requirements are `BR-nnn` (business), `FR-nnn` (functional),
`NFR-nnn` (non-functional), `UC-nn` (use case), `ADR-nnn` (decision),
`RISK-nnn`, `ASM-nnn`, `ISS-nnn`, `DEP-nnn` (RAID). Identifiers are permanent:
a withdrawn requirement is marked `Withdrawn`, never deleted or reused.

**Priority.** MoSCoW — `M` must, `S` should, `C` could, `W` won't (this release).

**Diagrams.** Mermaid, rendered inline by GitHub, GitLab and VS Code. Source is
in the Markdown, so diagrams are reviewed in the same pull request as the text
they describe.

**Status values.** `Draft` → `For review` → `Approved` → `Baselined`. Only a
baselined document may be referenced by a build ticket.

**Change control.** After baseline, any change is raised as a change request
against the owning document, assessed for traceability impact using
AMLI-RTM-001, and approved by the document approver.

---

## 5. Status

| Document | Version | Status | Owner |
|---|---|---|---|
| AMLI-GLO-001 | 0.1 | Draft | Business Analyst |
| AMLI-BRD-001 | 0.1 | Draft | Product Owner |
| AMLI-FRS-001 | 0.1 | Draft | Business Analyst |
| AMLI-NFR-001 | 0.1 | Draft | Solution Architect |
| AMLI-UC-001 | 0.1 | Draft | Business Analyst |
| AMLI-HLD-001 | 0.1 | Draft | Solution Architect |
| AMLI-ADR-001 | 0.1 | Draft | Solution Architect |
| AMLI-DFD-001 | 0.1 | Draft | Solution Architect |
| AMLI-PAT-001 | 0.1 | Draft | Engineering Lead |
| AMLI-LLD-001 | 0.1 | Draft | Engineering Lead |
| AMLI-DM-001 | 0.1 | Draft | Data Architect |
| AMLI-DDL-001 | 0.1 | Draft | Data Architect |
| AMLI-DD-001 | 0.1 | Draft | Data Architect |
| AMLI-API-001 | 0.1 | Draft | Engineering Lead |
| AMLI-API-002 | 0.1 | Draft | Engineering Lead |
| AMLI-INT-001 | 0.1 | Draft | Integration Architect |
| AMLI-SEC-001 | 0.1 | Draft | Security Architect |
| AMLI-MRM-001 | 0.1 | Draft | Model Risk Lead |
| AMLI-TST-001 | 0.1 | Draft | Test Lead |
| AMLI-OBS-001 | 0.1 | Draft | SRE Lead |
| AMLI-OPS-001 | 0.1 | Draft | SRE Lead |
| AMLI-RTM-001 | 0.1 | Draft | Business Analyst |
| AMLI-RAID-001 | 0.1 | Draft | Delivery Lead |
| AMLI-PLAN-001 | 0.1 | Draft | Delivery Lead |
| AMLI-SDLC-001 | 0.1 | Draft | Engineering Lead |
