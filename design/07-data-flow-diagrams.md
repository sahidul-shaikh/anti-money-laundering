# Data Flow Diagrams and Trust Boundaries

| | |
|---|---|
| **Document ID** | AMLI-DFD-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Solution Architect |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Notation and classification

Processes are rounded, data stores are cylinders, external entities are
rectangles, trust boundaries are subgraph frames. Every flow crossing a
boundary is enumerated in §5 with its classification and control.

| Class | Meaning | Examples |
|---|---|---|
| **C1 — Customer PII** | Identifies a natural person | Name, DOB, address, occupation, income, account number |
| **C2 — Transaction detail** | Financial activity, re-identifiable in combination | Amount, date, reference, counterparty, medium |
| **C3 — Suspicion-bearing** | Reveals that a party is under investigation. **Disclosure is a criminal offence.** | Alert existence, case status, finding, SAR narrative |
| **C4 — Operational** | System behaviour without customer content | Latency, token counts, cost, error codes |
| **C5 — Public / reference** | No customer content | Rule thresholds, scenario codes, policy text |

C3 is the controlling classification: anything derived from it inherits it.

---

## 2. Level 0 — Context

```mermaid
graph LR
  SAM[Actimize SAM]
  KYC[KYC / Party master]
  AO[Actimize ActOne]
  BR[Amazon Bedrock]
  AN[Analyst / Investigator]
  SIEM[SIEM]

  P0(("AML Alert<br/>Investigator"))

  SAM -->|F1 alerts, transactions C1,C2| P0
  KYC -->|F2 party context C1| P0
  P0 -->|F3 prompt C1,C2,C3| BR
  BR -->|F4 completion C3| P0
  P0 -->|F5 recommendation + evidence pack C3| AO
  P0 <-->|F6 review, decision C3| AN
  P0 -->|F7 security + audit events C4| SIEM
```

There is no flow from the system to any customer-facing channel. That absence is
a control (FR-090), not an omission.

---

## 3. Level 1 — Internal processes

```mermaid
graph TB
  subgraph ext[External]
    SAM[Actimize SAM]
    AO[Actimize ActOne]
    BR[Amazon Bedrock]
    AN[Analyst]
  end

  subgraph tb1[Trust boundary 1: ingestion perimeter]
    P1(("1.0 Ingest<br/>and validate"))
  end

  subgraph tb2[Trust boundary 2: application VPC]
    P2(("2.0 Capture<br/>evidence"))
    P3(("3.0 Resolve<br/>rule"))
    P4(("4.0 Render<br/>context"))
    P5(("5.0 Route<br/>and call"))
    P6(("6.0 Parse and<br/>ground"))
    P7(("7.0 Present<br/>and decide"))
    P8(("8.0 Write<br/>back"))
    P9(("9.0 Evaluate<br/>and improve"))
  end

  subgraph tb3[Trust boundary 3: data at rest]
    D1[(D1 Investigation DB)]
    D2[(D2 Evidence objects)]
    D3[(D3 Rule catalogue)]
    D4[(D4 Ledger / audit)]
  end

  SAM -->|F1| P1 --> D1
  P1 -->|quarantine| D1
  D1 --> P2 --> D2
  D3 --> P3
  P2 --> P4
  P3 --> P4
  P4 -->|F3 enveloped prompt| P5
  P5 -->|F3| BR
  BR -->|F4| P5
  P5 --> P6 --> D1
  P5 --> D4
  P6 --> D4
  D1 --> P7
  D2 --> P7
  P7 <-->|F6| AN
  P7 --> D1
  P7 --> P8 -->|F5| AO
  D4 --> P9 --> D1
```

### Process descriptions

| # | Process | In | Out | Store |
|---|---|---|---|---|
| 1.0 | Ingest and validate | Source records (C1, C2) | Normalised records, quarantine entries | D1 |
| 2.0 | Capture evidence | Alert, party, account, transactions (C1, C2) | Hashed snapshots, access records | D2, D1 |
| 3.0 | Resolve rule | Scenario, effective date (C5) | Rule text, thresholds, citation (C5) | D3 |
| 4.0 | Render context | Evidence + rule | Investigation prompt with envelope (C1, C2) | — |
| 5.0 | Route and call | Prompt | Completion, token and cost records (C3, C4) | D4 |
| 6.0 | Parse and ground | Completion | Verdict, findings, groundedness (C3) | D1, D4 |
| 7.0 | Present and decide | Recommendation, findings, evidence | Decision, override reason (C3) | D1 |
| 8.0 | Write back | Recommendation, evidence pack (C3) | Case note in ActOne | — |
| 9.0 | Evaluate and improve | Ledger, decisions, labels (C3, C4) | Clusters, proposals, evaluations | D1 |

---

## 4. Level 2 — Process 5.0, route and call

The detail matters here because this is where untrusted data meets a model and
where cost is incurred.

```mermaid
graph TB
  IN[Rendered context<br/>C1 C2 enveloped] --> G1(("5.1 Pre-call<br/>guardrail"))
  G1 -->|block| BL[Control check: blocked<br/>run terminated safely]
  G1 -->|allow| R1(("5.2 Select<br/>model"))
  R1 --> C1(("5.3 Invoke<br/>via gateway"))
  C1 -->|provider error| FB(("5.4 Fallback<br/>provider/model"))
  FB --> C1
  C1 --> AC(("5.5 Account<br/>tokens and cost"))
  AC --> G2(("5.6 Post-call<br/>guardrail"))
  G2 -->|tipping-off or<br/>egress violation| BL2[Security event<br/>fail closed]
  G2 -->|allow| OUT[Completion to 6.0]

  AC --> LD[(D4 Ledger:<br/>model_call)]
  G1 --> CC[(D1 control_check)]
  G2 --> CC
  BL2 --> SE[(D1 security_event)]
  R1 --> CAP{Spend cap<br/>exceeded?}
  CAP -->|yes| AB[Abort: budget_exceeded<br/>operator alert]
```

**Invariants enforced here**

| Invariant | Control |
|---|---|
| No call without a pre-call guardrail evaluation | 5.1 is not bypassable; the gateway rejects a call without a control-check token |
| No completion reaches parsing without a post-call guardrail | 5.6 ordered after accounting so a blocked call is still costed and visible |
| Every call is accounted even when it fails | 5.5 runs on the error path as well as the success path |
| Spend cap stops work rather than degrading quality | Abort, not silently switch to a cheaper model |

---

## 5. Trust boundaries and crossing flows

```mermaid
graph LR
  subgraph TB0[TB-0 Internet]
    U[Browser]
  end
  subgraph TB1[TB-1 Client estate]
    SAM2[SAM / ActOne / KYC]
  end
  subgraph TB2[TB-2 AWS account, VPC]
    APP[Application tier]
    DATA[(Data tier)]
  end
  subgraph TB3[TB-3 AWS managed services]
    BRS[Bedrock]
    S3S[S3]
  end
  U -->|X1| APP
  SAM2 -->|X2| APP
  APP -->|X3| SAM2
  APP -->|X4| BRS
  APP -->|X5| S3S
  APP -->|X6| DATA
```

| ID | Flow | Class | Direction | Controls |
|---|---|---|---|---|
| **X1** | Reviewer browser ↔ Investigation API | C1, C2, C3 | Both | TLS 1.3, WAF, OIDC with MFA, RBAC, RLS, short-lived session, no C3 in URLs or query strings |
| **X2** | SAM / KYC → Ingestion | C1, C2 | Inbound | Private connectivity or mTLS, schema validation, quarantine on failure, institution tagging, no inbound executable content |
| **X3** | Write-back → ActOne | C3 | Outbound | mTLS, idempotency key, least-privilege service account with note-write only, **no status mutation capability** |
| **X4** | LLM Gateway → Bedrock | C1, C2, C3 | Outbound | VPC endpoint (no internet egress), in-region only, CMK, no-training contractual term, prompt captured and hashed, spend cap |
| **X5** | Evidence Collector ↔ S3 | C1, C2, C3 | Both | VPC endpoint, CMK, Object Lock, bucket policy denying unencrypted or cross-region access |
| **X6** | Application ↔ Aurora | C1, C2, C3 | Both | IAM auth, TLS, RLS session context set on acquisition, insert-only grant on audit tables |

### The boundary that does not exist

There is no flow from any process to a customer channel — no email, SMS,
statement, chatbot or portal integration. This is enforced by the absence of any
such adapter and by the post-call guardrail failing closed on customer-directed
content (FR-090). Adding one would require a new trust-boundary crossing, a
threat-model revision and MLRO approval.

---

## 6. Data at rest

| Store | Contents | Class | Encryption | Retention | Immutability |
|---|---|---|---|---|---|
| D1 Investigation DB | Alerts, cases, parties, accounts, transactions, runs, findings, decisions | C1, C2, C3 | CMK at rest, TLS in transit | 7 years | Audit tables insert-only |
| D2 Evidence objects | Captured snapshots | C1, C2, C3 | CMK, SSE-KMS | 7 years | S3 Object Lock, compliance mode |
| D3 Rule catalogue | Thresholds, rule text, citations | C5 | CMK | Indefinite, versioned | Append-only versions |
| D4 Ledger / audit | Model calls, control checks, security events, audit events | C3, C4 | CMK | 7 years | Insert-only, daily hash-chain verification |
| Telemetry | Metrics, traces, logs | C4 only | CMK | 90 days hot, 1 year archive | — |

**Telemetry carries no C1, C2 or C3.** Correlation to an investigation is by
`trace_id` and `run_id` only, and the mapping from those to customer data lives
behind the same access control as the data itself (NFR-047, ADR-017).

---

## 7. Flows that are deliberately absent

Recorded because an absent flow is a design decision and should be reviewable.

| Absent flow | Why |
|---|---|
| Customer data → non-production environments | NFR-047; masked or synthetic only |
| Customer data → model training or fine-tuning | NFR-049; contractual and architectural |
| Agent → alert or case status mutation in SAM/ActOne | ADR-013, FR-075 |
| Agent → regulatory filing endpoint | BR-003, FR-071 |
| Agent → any customer channel | BR-004, FR-090 |
| Model → groundedness judgement | ADR-004 |
| Label or adjudication → rendered prompt | FR-033 |
| Label → failure clustering features | FR-079 |
| Cross-jurisdiction customer data | ADR-014 |
