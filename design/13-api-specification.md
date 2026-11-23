# API Specification

| | |
|---|---|
| **Document ID** | AMLI-API-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Engineering Lead |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

Machine-readable contract: [`14-openapi.yaml`](14-openapi.yaml) (AMLI-API-002).

---

## 1. Conventions

| Aspect | Rule |
|---|---|
| **Base path** | `https://{host}/api/v1` |
| **Versioning** | Major version in the path. Breaking changes require a new major version; additive changes do not |
| **Media type** | `application/json; charset=utf-8`. Problem responses use `application/problem+json` (RFC 9457) |
| **Identifiers** | UUID v7 in all paths. Source identifiers appear as `externalReference`, never in a path |
| **Casing** | `camelCase` in JSON, `snake_case` in the database. Mapping is explicit in the schema layer |
| **Timestamps** | RFC 3339, UTC, with offset `Z`. Business dates are `YYYY-MM-DD` |
| **Money** | `{"amount": "9000.00", "currency": "USD"}` — amount is a **string** to avoid float round-tripping |
| **Pagination** | Cursor-based: `?limit=50&cursor=…`; response carries `nextCursor`. Offset paging is not offered |
| **Sorting** | `?sort=raisedAt:desc`. Allow-listed fields only |
| **Idempotency** | Every `POST` that creates state requires an `Idempotency-Key` header. Replay within 24 h returns the original response with `Idempotent-Replay: true` |
| **Concurrency** | `ETag` on mutable resources; `If-Match` required on update. Mismatch returns 409 |
| **Rate limit** | Per principal. `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` on every response |
| **Correlation** | `X-Trace-Id` accepted and echoed; generated when absent |

### No C3 in URLs

Alert identifiers, case identifiers and party names are suspicion-bearing (C3).
They never appear in query strings, which are logged by intermediaries. Filtered
reads use `POST /searches` with a body, not `GET` with parameters.

---

## 2. Authentication and authorisation

OIDC bearer tokens from the enterprise IdP. The token carries `sub`,
`institution_id`, `jurisdictions[]` and `roles[]`.

| Role | Permissions |
|---|---|
| `amli.analyst` | Read assigned queue; create decisions of type accept, override, request information |
| `amli.investigator` | Analyst, plus case creation, alert linking, finding authoring |
| `amli.manager` | Investigator, plus reassignment, queue administration, quality sampling |
| `amli.mlro` | Read all; approve report versions |
| `amli.validator` | Read all; run evaluations; no decision rights |
| `amli.compliance_admin` | Manage policy, thresholds, configuration proposals |
| `amli.operator` | Operational endpoints; no access to customer data |
| `amli.auditor` | Read-only across all investigation data and audit events |

Every request sets the database session context from the token before any query
(ADR-014). Authorisation is enforced server-side; the workspace reflects it but
does not implement it (FR-097).

---

## 3. Resources

```
/alerts                     GET  POST(search)
/alerts/{alertId}           GET
/alerts/{alertId}/evidence  GET
/alerts/{alertId}/recommendation  GET
/alerts/{alertId}/investigate     POST   (operator / replay)
/cases                      GET  POST
/cases/{caseId}             GET  PATCH
/cases/{caseId}/alerts      GET  POST  DELETE
/cases/{caseId}/findings    GET  POST
/cases/{caseId}/evidence    GET
/decisions                  POST
/decisions/{decisionId}     GET
/consolidation-proposals    GET
/evidence/{evidenceId}      GET
/evidence/{evidenceId}/content   GET
/runs/{runId}               GET
/runs/{runId}/calls         GET
/runs/{runId}/controls      GET
/rules                      GET
/rules/{scenarioCode}       GET
/evaluations                GET  POST
/proposals                  GET  POST
/proposals/{proposalId}/approval  POST
/admin/queues               GET
/admin/quarantine           GET  POST(reprocess)
/health /ready /metrics
```

---

## 4. Key endpoints

### 4.1 Get a recommendation

```http
GET /api/v1/alerts/0192f3a1-…/recommendation
Authorization: Bearer …
```

```json
{
  "recommendationId": "0192f3b2-…",
  "alertId": "0192f3a1-…",
  "runId": "0192f3a9-…",
  "disposition": "close_no_further_action",
  "reasoning": "Four credits of 3,960.00 USD on the 26th of each month are consistent with the declared annual income of 68,900.00 USD for a serving member of the armed forces. The 12,672.00 USD debit two days after the fourth credit is a single outgoing payment and does not satisfy the recurrence requirement of AML-STR-CCE-INN-A-D01-DST.",
  "confidence": 0.86,
  "groundedness": 1.0,
  "citedCount": 5,
  "inventedCount": 0,
  "rule": {
    "ruleId": "AML-STR-CCE-INN-A-D01-DST",
    "detectionModel": "AML-STR",
    "sourceDocument": "Actimize AML SAM 8.5.0 Solution Guide",
    "sourcePage": 509,
    "catalogueVersion": "2026.11.1"
  },
  "findings": [
    {
      "findingId": "0192f3c4-…",
      "statement": "The four monthly credits are salary consistent with declared income.",
      "grounded": true,
      "reviewStatus": "final",
      "evidence": [
        { "evidenceId": "0192f3d0-…", "citation": "2000000039", "stance": "supports", "resolved": true },
        { "evidenceId": "0192f3d0-…", "citation": "2000000040", "stance": "supports", "resolved": true }
      ]
    },
    {
      "findingId": "0192f3c5-…",
      "statement": "A single debit does not meet the recurrence threshold.",
      "grounded": true,
      "reviewStatus": "final",
      "evidence": [
        { "evidenceId": "0192f3d1-…", "citation": "2000000043", "stance": "contradicts", "resolved": true }
      ]
    }
  ],
  "cost": { "amount": "0.0112", "currency": "USD" },
  "producedAt": "2026-11-18T09:14:22Z"
}
```

**`stance: "contradicts"`** is carried on the wire because it is substantive:
the agent is citing the transaction that *triggered* the alert and explaining
why it does not satisfy the rule. An investigator needs to see that.

### 4.2 Record a decision

```http
POST /api/v1/decisions
Idempotency-Key: 7f1c…
If-Match: "W/\"alert-rev-14\""
Content-Type: application/json
```

```json
{
  "alertId": "0192f3a1-…",
  "recommendationId": "0192f3b2-…",
  "outcome": "override_escalate",
  "rationale": "Prior alert on the same party three weeks ago was also closed. Pattern across alerts warrants a case.",
  "overrideReasonCode": "missed_context"
}
```

`201 Created` with `Location` and the created decision. Failure modes:

| Status | Condition |
|---|---|
| 400 | `overrideReasonCode` absent on an override outcome |
| 403 | Principal lacks the escalation permission for the jurisdiction |
| 409 | `If-Match` stale — another reviewer decided first |
| 422 | Recommendation does not belong to the alert |
| **500** | **Actor resolved to a system principal.** The database trigger refuses; this is a defect, raised as P1, never surfaced as a user error |

### 4.3 Link an alert into a case

```http
POST /api/v1/cases/{caseId}/alerts
Idempotency-Key: …
```

```json
{ "alertId": "0192f3a1-…", "reason": "Same party, overlapping period, same typology." }
```

`reason` is mandatory (FR-055). Unlinking is `DELETE` with a reason in the body;
the row is not removed, `unlinkedAt` and `unlinkedBy` are set.

### 4.4 Reconstruct a run

```http
GET /api/v1/runs/{runId}
```

```json
{
  "runId": "0192f3a9-…",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "status": "completed",
  "deploymentId": "0192e1c0-…",
  "ruleCatalogueVersion": "2026.11.1",
  "agentConfigHash": "9f2b…",
  "escalations": 1,
  "cost": { "amount": "0.0112", "currency": "USD" },
  "startedAt": "2026-11-18T09:14:09Z",
  "endedAt": "2026-11-18T09:14:22Z",
  "calls": [
    { "attempt": 1, "tier": "cheap",   "modelIdentifier": "us.meta.llama3-3-70b-instruct-v1:0",
      "tokensIn": 3412, "tokensOut": 288, "latencyMs": 2380, "status": "ok",
      "promptStorageUri": "s3://…/prompts/…", "systemPromptHash": "a1c4…" },
    { "attempt": 2, "tier": "premium", "modelIdentifier": "mistral.mistral-large-3-675b-instruct",
      "tokensIn": 3412, "tokensOut": 402, "latencyMs": 7910, "status": "ok",
      "promptStorageUri": "s3://…/prompts/…", "systemPromptHash": "a1c4…" }
  ],
  "controls": [
    { "controlName": "EnvelopeAssertion", "phase": "pre_call",  "outcome": "allow" },
    { "controlName": "TippingOffGuard",   "phase": "post_call", "outcome": "allow" }
  ],
  "evidence": [ { "evidenceId": "0192f3d0-…", "accessPurpose": "transaction_history", "contentHash": "3c9e…" } ]
}
```

This single response is what satisfies UC-09 and NFR-029.

### 4.5 Operator re-investigation

```http
POST /api/v1/alerts/{alertId}/investigate
```

Requires `amli.operator` or `amli.compliance_admin`. Creates a **new** run; it
never overwrites a previous one. Used for replay after a defect fix and for
challenger comparison.

---

## 5. Error model

RFC 9457 problem details, with a stable `type` URI.

```json
{
  "type": "https://amli.example.com/problems/label-integrity",
  "title": "Label integrity violation",
  "status": 422,
  "detail": "A CTR-only outcome cannot produce an inferred escalate label.",
  "instance": "/api/v1/alerts/0192f3a1-…",
  "traceId": "4bf92f35…",
  "violations": [
    { "field": "labelBasis", "code": "ctr_cannot_infer_suspicion" }
  ]
}
```

| Status | Meaning | Retry |
|---|---|---|
| 400 | Malformed request | No |
| 401 | Missing or invalid token | No |
| 403 | Authenticated but not permitted | No |
| 404 | Not found, or not visible in this jurisdiction | No |
| 409 | Version conflict, or duplicate with a different body under the same idempotency key | Refresh and retry |
| 422 | Semantically invalid, including domain-rule violations | No |
| 429 | Rate limited | Yes, after `Retry-After` |
| 500 | Internal | Yes, idempotently |
| 503 | Dependency unavailable | Yes, after `Retry-After` |

A 404 is deliberately returned rather than 403 when a resource exists in another
jurisdiction. Distinguishing them would leak the existence of an investigation.

---

## 6. Event contracts

Published to EventBridge; consumed internally and, optionally, by the client's
data platform.

| Event | Payload class | Trigger |
|---|---|---|
| `amli.alert.ingested` | C4 identifiers only | Ingestion committed |
| `amli.run.completed` | C4 + disposition | Run closed successfully |
| `amli.recommendation.created` | C4 identifiers only | Recommendation persisted |
| `amli.decision.recorded` | C4 identifiers + outcome | Decision committed |
| `amli.writeback.required` | C4 identifiers | Outbox relay |
| `amli.security.event` | C4 + threat type + severity | Security event raised |
| `amli.budget.exceeded` | C4 + amounts | Spend cap breached |

**Events carry identifiers, never customer content.** A consumer that needs
detail calls the API with its own authorisation, which is where jurisdiction
scoping is applied.

```json
{
  "specversion": "1.0",
  "type": "amli.decision.recorded",
  "source": "/amli/investigation-api",
  "id": "0192f400-…",
  "time": "2026-11-18T09:20:03Z",
  "subject": "alert/0192f3a1-…",
  "data": {
    "institutionId": "0192a000-…",
    "alertId": "0192f3a1-…",
    "decisionId": "0192f3f0-…",
    "outcome": "override_escalate",
    "agreedWithRecommendation": false,
    "traceId": "4bf92f35…"
  }
}
```

---

## 7. Backward compatibility rules

| Change | Allowed in a minor version |
|---|---|
| Adding an optional request field | Yes |
| Adding a response field | Yes — clients must tolerate unknown fields |
| Adding an enum value | **No** for request enums; **yes** for response enums, and clients must handle unknown values |
| Removing or renaming a field | No |
| Tightening validation | No |
| Changing a default | No |
| Adding a required header | No |

Response enums may grow because `disposition`, `overrideReasonCode` and
`threatType` are expected to. Clients are contractually required to treat an
unrecognised value as "other" rather than failing.
