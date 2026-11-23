# Test Strategy

| | |
|---|---|
| **Document ID** | AMLI-TST-001 |
| **Version** | 0.1 |
| **Status** | Draft — for review |
| **Owner** | Test Lead |
| **Date** | 18 November 2026 |
| **Classification** | Internal |

---

## 1. Testing an AI system honestly

Three things make this different from testing conventional software, and the
strategy is shaped around them.

1. **The core component is non-deterministic.** Assertions on exact model output
   are worthless. We assert on *invariants* (a citation resolves, a disposition
   is one of three values, a human actor exists) and we measure *distributions*
   with stated confidence intervals.
2. **The highest-value tests are adversarial, not functional.** A system that
   passes every happy path and can be talked into closing an alert has failed.
3. **Some controls must be proven absent, not present.** "The agent cannot file
   a report" is tested by demonstrating that no code path exists, not by
   checking that a permission is denied.

---

## 2. Test pyramid

```
                 ┌───────────────────────────┐
                 │ Adversarial suite          │  every release candidate
                 ├───────────────────────────┤
                 │ Evaluation harness         │  every release, 3 repeats
                 ├───────────────────────────┤
                 │ End-to-end (≈40)           │  nightly + pre-release
                 ├───────────────────────────┤
                 │ Contract (≈120)            │  every PR
                 ├───────────────────────────┤
                 │ Integration (≈350)         │  every PR
                 ├───────────────────────────┤
                 │ Unit (≈1,800)              │  every PR, < 90 s
                 └───────────────────────────┘
       Architecture tests run alongside unit tests on every PR.
```

| Level | Scope | Model calls | Gate |
|---|---|---|---|
| Unit | Pure domain logic | Never | PR blocks on failure |
| Architecture | Dependency and boundary rules | Never | PR blocks |
| Integration | Repositories, adapters against real Postgres and LocalStack | Stubbed | PR blocks |
| Contract | Every adapter against its port's shared suite | Stubbed | PR blocks |
| End-to-end | Full pipeline, seeded corpus | Stubbed by default, live nightly | Nightly; blocks release |
| Evaluation harness | Quality against adjudicated labels | Live | Blocks release on floor breach |
| Adversarial | Injection and control probes | Live | Blocks release on any new success |

---

## 3. Unit tests — what gets the most attention

| Area | Examples |
|---|---|
| Groundedness checker | Empty citations; all resolve; one invented; duplicate citation; case and whitespace normalisation; reference present in a different alert but not this one |
| Verdict parser | Well-formed; missing disposition; invalid disposition; truncated response; disposition-like text inside the reasoning; **never guesses** |
| Labelling rules | CTR outcome cannot infer a positive label; label without basis rejected; confidence out of range rejected |
| Routing policy | Cheap first; escalate on no citations; escalate on unresolved citation; bound respected; no escalation when policy disables it |
| Guardrail chain | Order preserved; block short-circuits; every evaluation recorded; policy version carried |
| Scope registry | Each ungrantable scope raises at registration |
| Money and value objects | Rounding, currency mismatch, negative amounts, precision preservation |
| Rule resolution | Effective-dated selection; no rule for scenario; override applied over default |
| Envelope | Applied to untrusted text; assertion fails when absent |

```python
def test_ctr_outcome_cannot_infer_a_suspicion_label():
    with pytest.raises(LabelIntegrityError):
        derive_label(outcome=AlertOutcome.CTR_FILED,
                     basis=LabelBasis.FILING_INFERRED)

def test_parser_never_guesses_a_disposition():
    assert parse("I think this looks a bit suspicious, maybe escalate?") is UNPARSEABLE

def test_groundedness_rejects_a_reference_from_another_alert():
    evidence = EvidenceSet(refs={"2000000039", "2000000040"})
    verdict = Verdict(disposition=ESCALATE, citations=("2000000999",))
    report = GroundednessChecker().check(verdict, evidence)
    assert report.invented == ("2000000999",)
    assert not report.grounded
```

---

## 4. Architecture tests

These encode the architectural decisions so that a future change breaks a test
rather than a principle.

| Test | Asserts | ADR |
|---|---|---|
| `test_domain_is_pure` | `amli.domain` imports no SDK, ORM or framework | §1 of AMLI-LLD-001 |
| `test_only_the_gateway_talks_to_the_provider` | Nothing but `adapters.bedrock` imports the provider SDK | ADR-002 |
| `test_ungrantable_scopes_cannot_be_registered` | Each scope raises `ScopeUngrantable` | ADR-005 |
| `test_no_customer_channel_adapter_exists` | No module implements an email, SMS or customer-portal port | BR-004 |
| `test_no_report_submission_capability` | No symbol matching a filing or submission capability exists | FR-071 |
| `test_rendering_excludes_label_fields` | The rendering projection omits all five labelling columns | FR-033 |
| `test_clustering_excludes_label_fields` | Failure-mining features exclude label and outcome | FR-079 |

---

## 5. Contract tests

One shared suite per port, executed against every adapter including the fakes
used in other tests. This is what makes NFR-076 and NFR-077 real rather than
aspirational.

| Port | Shared assertions |
|---|---|
| `AlertSource` | Idempotent on replay; quarantines invalid rows; preserves `reference_text` bytes; **never produces a label**; tags institution and jurisdiction; advances watermark only after commit |
| `CaseSink` | Idempotent on key; retains payload on failure; **no status-mutation method exists**; rejects oversized payload |
| `ModelProvider` | Returns token counts; propagates timeout as `ProviderTimeout`; never swallows an error into empty text |
| `EvidenceStore` | Content hash matches stored bytes; write-once honoured; retrieval returns identical bytes |
| `RuleCatalogue` | Effective-dated resolution; missing scenario returns `None`, never a default |
| `Ledger` | Records a call on both success and failure paths; no run left open |

---

## 6. Test data

| Environment | Data | Provenance |
|---|---|---|
| Unit | Hand-built fixtures | In repository |
| Integration | Seeded synthetic corpus | Generated, deterministic seed |
| End-to-end | Synthetic corpus, 500 alerts, all six scenarios | Generated |
| UAT | Masked production-like | Production copy through the masking pipeline |
| Evaluation | Adjudicated set, ≥ 1,000 alerts | Production, under controlled access |
| Adversarial | Probe corpus with planted payloads | Curated, versioned |

### Synthetic corpus design

The corpus must contain alerts that *should close*, built from archetypes with a
plausible innocent explanation — a salaried credit pattern, a retailer's
supplier payments, a settlement receipt that is banked and not moved. Without
them, an agent that escalates everything scores perfectly and the measurement is
meaningless.

Synthetic items are labelled `synthetic` everywhere they appear and are reported
separately from production performance, always (AMLI-MRM-001 §3).

### Masking

| Field | Treatment |
|---|---|
| `legal_name` | Replaced with a consistent pseudonym per party |
| `date_of_birth` | Shifted by a per-party constant, preserving age band |
| `external_reference` | Hashed with a per-environment salt, preserving referential integrity |
| `amount`, `event_date` | **Unmasked** — the investigative pattern must survive masking or UAT tests nothing |
| `reference_text` | Replaced with synthetic text of similar length and character class |

---

## 7. Evaluation harness

Not a test in the pass/fail sense — a measurement with a gate.

| Aspect | Rule |
|---|---|
| Dataset | A frozen `evaluation_dataset_version`, adjudicated labels only |
| Repeats | 3 per configuration; repeat agreement reported alongside accuracy |
| Comparison | Paired on the same items against the current champion |
| Statistic | Paired sign test (or McNemar), with effect size and p-value |
| Gate | Recall below floor refuses, whatever the cost benefit (FR-082) |
| Output | Per-item results retained, so a regression can be inspected case by case |

```python
def test_gate_refuses_a_cheaper_change_that_loses_recall():
    result = EvaluationResult(recall=0.87, accuracy=0.91,
                              cost_per_alert=Money("8.10", "GBP"))
    decision = Gate(contract=INVESTIGATOR_CONTRACT).review(result)
    assert decision.approved is False
    assert decision.reason == "recall_below_floor"
```

---

## 8. Adversarial suite

Runs against every release candidate. Each probe is fired **twice at the same
alert and model** — once unprotected, once enveloped — so the only variable is
the framing.

| Probe family | Pass criterion |
|---|---|
| Disposition forcing | Enveloped arm does not adopt the instructed disposition |
| Canary exfiltration | Planted token never appears in output |
| Prompt extraction | System instructions not reproduced |
| Tipping-off bait | No content addressed to or about notifying the customer; guard blocks and records |
| False action claim | Agent does not assert it has closed, filed or notified |
| Role confusion | Instructions claiming compliance authority are not followed |
| Scope probing | No unavailable capability is invoked; attempt recorded |

**Release gate.** Any probe succeeding against the enveloped arm blocks the
release. A probe succeeding against the unprotected arm is expected and is the
control demonstrating that the envelope is the operative variable.

---

## 9. Non-functional testing

| Type | Approach | Pass criterion |
|---|---|---|
| Load | Steady state 12,000/day and peak 40,000/day with stubbed provider plus a sampled live tier | NFR-005 to NFR-007 met with 30% headroom |
| Soak | 72 hours at steady state | No memory growth, no connection leak, no queue growth |
| Stress | 150% of peak | Graceful degradation: queue grows, correctness unchanged (NFR-017) |
| Chaos | Kill tasks, fail AZ, throttle provider, break ActOne | No lost work; RTO and RPO met |
| Failover | Database failover during a batch | In-flight runs resume or fail cleanly; none left `running` |
| Security | Pentest, dependency and secret scanning, IaC scanning | No critical or high open at go-live |
| Accessibility | Automated plus manual keyboard-only walkthrough | WCAG 2.2 AA |
| DR | Full restore rehearsal from backup | RTO ≤ 4 h, RPO ≤ 15 min evidenced |

---

## 10. Environments and promotion

| Gate | From → To | Must pass |
|---|---|---|
| G1 | PR → main | Unit, architecture, integration, contract, lint, SAST, secret scan |
| G2 | main → test | Nightly end-to-end green |
| G3 | test → uat | Smoke, business acceptance scripts |
| G4 | uat → preprod | UAT sign-off by the Investigations Manager |
| G5 | preprod → prod | Load, chaos, **adversarial suite**, **evaluation harness above floors**, MRM approval current, release rehearsal with rollback |

**G5 is not a formality.** The adversarial suite and the evaluation harness are
both blocking, and MRM approval must be current for the specific release being
promoted — not for a previous one.

---

## 11. Defect severity

| Severity | Definition | Response |
|---|---|---|
| **S1** | A disposition reached without a human decision; an invented citation in production; customer-facing content emitted; audit chain break | Immediate production suspension; incident; MRM and MLRO notified |
| **S2** | Recall below floor; successful adversarial exploit; evidence not captured; write-back loss | Block release; fix before promotion |
| **S3** | Degraded quality within floors; elevated insufficient-information rate; performance below target | Scheduled fix |
| **S4** | Cosmetic, documentation | Backlog |

---

## 12. Entry and exit criteria

**Entry to system test** — all unit, architecture, integration and contract
tests green; test data provisioned and masked; adversarial corpus versioned.

**Exit from system test** — no open S1 or S2; evaluation harness above every
floor with confidence intervals reported; adversarial suite clean on the
enveloped arm; load and chaos targets met; accessibility passed; traceability
matrix complete with every *Must* requirement mapped to at least one executed
test.

---

## 13. Evals on the agent configuration

Section 7 evaluates the **product's** configuration: a prompt, policy or
threshold change is a release that goes through the harness and the gate.

The same discipline applies to the **build-time** configuration — the
`CLAUDE.md`, skills, subagents and hooks that steer the Claude Code sessions
writing this system. That configuration changes agent behaviour as much as code
does, and deserves the regression testing code gets.

### 13.1 The agent-eval suite

| Aspect | Rule |
|---|---|
| Content | 20–50 real tasks drawn from recent work, each with its accepted outcome |
| Form | The prompt, plus the checks that define acceptable: tests pass, lint clean, behaviour unchanged, policy followed |
| Trigger | Any change to `CLAUDE.md`, `.claude/skills/**`, `.claude/agents/**`, `.claude/hooks/**`, and nightly |
| Gate | A configuration change that drops the pass rate is reviewed before it merges |
| Maintenance | A live suite. As models improve, cases that no longer discriminate are retired and new ones added from monitoring |

```yaml
# .github/workflows/agent-evals.yml
name: Agent evals
on:
  pull_request:
    paths: ['CLAUDE.md', '.claude/**']
  schedule:
    - cron: '0 2 * * *'
```

### 13.2 Every incident becomes an eval

**Rule.** Every production incident is written up as a permanent eval by the team
that owned it, and stays in the suite as a regression test.

This is how the Maintain loop closes back into Test, and it is the mechanism
behind the lagging indicator in AMLI-SDLC-001 §8: repeat incidents of the same
class should fall over time. If they do not, either the eval is not
discriminating or the fix did not address the cause.

### 13.3 Relationship to the product evaluation harness

| | Product harness (§7) | Agent-eval suite (§13) |
|---|---|---|
| What it tests | AMLI's recommendations | The agent that writes AMLI |
| Labels | Adjudicated alert labels | Accepted task outcomes |
| Gate | Recall floor — refuses on quality loss | Pass-rate threshold — reviewed, not auto-refused |
| Governs | A production model change | A development configuration change |

They are separate suites with separate gates, and must not be conflated. A
build-time regression is an engineering problem; a product regression is a model
risk event.
