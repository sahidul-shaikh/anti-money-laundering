# AML Alert Investigator - product architecture

Everything needed to build, run and govern the AML alert investigator, and
nothing else.

**Out of scope on purpose.** The pillar console (`scripts/serve_factory.py`,
`scripts/ui/`), the twelve-stage build factory (`aml/build/`,
`scripts/run_build.py`), the deck and document generators and the demo input
helpers are presentation and tooling. They are not part of the product. If you
were handed this use case tomorrow, the modules below are what you would
build.

Read **[USE_CASE.md](USE_CASE.md)** first for the problem this answers.

---

## 1. The shape of it

Six packages under `aml/`. One direction of dependency: everything may use
`core`, nothing in `corpus` or `llm` knows about `run`, and `improve` sits on
top of all of it.

```
                    AntiMoneyLaundering/Alert_Final_table.xlsx
                    Actimize AML SAM 8.5.0 Solution Guide.pdf
                                  |
                 +----------------+----------------+
                 |                                 |
          aml/corpus/                     scripts/build_rule_catalogue.py
     load, synthesise, render                      |
                 |                        library/aml/rules.json
                 |                                 |
                 v                                 v
      +---------------------------------------------------------+
      |                        aml/run/                          |
      |  config -> prompts -> rules -> routing -> verdict        |
      |  engine (batch)              chat (single turn)          |
      +---------------------------------------------------------+
            |                    |                      |
            v                    v                      v
      aml/security/          aml/llm/               aml/core/
   envelope, injection,   fleet, router,              ledger
   emit, tools, probes      bedrock
            |                    |                      |
            +--------------------+----------------------+
                                 |
                                 v
                          aml/run/telemetry
                          aml/improve/
                 contract, bands, mining, optimise, tokenomics
```

The rule of the whole design: **anything asserted twice is asserted wrong.**
Every model call and every outcome is written to one ledger, and every figure
anywhere - cost, groundedness, accuracy, telemetry, the improvement decision -
is computed from it.

---

## 2. `aml/corpus/` - the alerts

What the investigator reads, and the labels the measurement scores against.

| Module | What it does |
|---|---|
| `model.py` | The shape of one alert: `Alert`, `Party`, `Account`, `Transaction`, and the label constants `ESCALATE` / `CLOSE`, `REAL` / `SYNTHETIC`. Frozen dataclasses - an alert is never mutated after loading. |
| `loader.py` | Reads the 35 real alerts out of the supplied extract. Every one of them escalated and filed, so each loads with label `ESCALATE`. That fact is the reason `synthetic.py` exists. |
| `synthetic.py` | Builds 35 alerts a competent investigator would close, from named archetypes - a salary read as layering, a shop paying suppliers, a settlement cheque banked and left alone. Seeded, so the corpus is reproducible. Labelled `SYNTHETIC` everywhere it appears. |
| `render.py` | Turns an alert into the text the investigator sees. **Carries no label and no rationale** - anything the harness scores against must be absent here, or the measurement is worthless. Takes a `guardrail` flag that decides whether reference text is enveloped. |
| `__init__.py` | `build_corpus()`, `write_corpus()`, `read_corpus()`, `summarise()`. The corpus is built once and cached to `artifacts/corpus.json`. |

Loaded corpus: **70 alerts, 35 escalate / 35 close, 1,073 transactions, 6
scenarios.** Balanced by construction.

---

## 3. `aml/run/` - the investigator

The agent itself. Seven modules, each one doing a single job.

| Module | What it does |
|---|---|
| `config.py` | `AgentConfig` - every behavioural flag the agent has, and `system_prompt()` which composes the standing instructions from it. The base prompt is **never edited**; approved changes are appended, so the stable prefix stays stable and a cache would keep working. Holds the rule texts the Improve pillar proposes, e.g. `EXPLAIN_BEFORE_ESCALATE`. |
| `prompts.py` | `SYSTEM_PROMPT` - the investigator's instructions and the disposition vocabulary - and `user_turn()`, which assembles the per-alert message. The detection thresholds are deliberately **not** here. |
| `rules.py` | Retrieves the detection rule the alert actually fired from `library/aml/rules.json`, by scenario code, with the page it came from. Replaces prose a person transcribed from a 677-page PDF with a citation. |
| `routing.py` | The **policy**: what to do when a cheap model answers but cannot show its working. `check_evidence()` verifies every citation against the alert; if an answer cites nothing, or cites a reference the alert does not contain, the policy escalates once to the premium tier. Deterministic, no judge model. Also holds `BROKEN_MODEL`, the non-existent model id used for fault injection. |
| `engine.py` | The batch path. `run_alert()` renders, routes, parses and grades one alert; `run_corpus()` does the whole corpus and writes to the ledger. Provider failures become a `Disposition` with an error, never an exception that loses the run. |
| `verdict.py` | `parse()` turns a model response into a `Verdict`; `grade()` scores it. **Groundedness is computed, not judged** - a cited reference either appears in the alert or it does not. |
| `chat.py` | The single-turn path: one alert, pasted or picked, sent by hand. Same prompts, same router, same grading as the batch engine. This is what the console's single-alert panels drive. |
| `telemetry.py` | Five layers computed from the ledger - **SYSTEM** (is it up), **MODEL** (what did it cost), **AGENT** (is it grounded), **TRANSACTION** (is it right), **VALUE** (is it worth running). Uptime and error rate answer none of the questions a regulator asks; these five do. |

### The path of one alert

```
Alert
  -> render()                       the investigator's view, no label
  -> rules.for_scenario()           the rule that fired + page citation
  -> user_turn()                    the message
  -> system_prompt(config)          the standing instructions
  -> Router.complete()              cheapest serving model above the floor
  -> parse()                        Verdict: disposition, reasoning, citations
  -> check_evidence()               every citation checked against the alert
       |- grounded      -> accept
       |- not grounded  -> escalate once to premium, then accept
  -> grade()                        correct? cited? invented anything?
  -> Ledger.record()                one call record, one outcome record
```

---

## 4. `aml/llm/` - the fleet and the router

| Module | What it does |
|---|---|
| `bedrock.py` | The **only** place the product talks to a model. One `BedrockProvider` over the Converse API, with retry and a typed `ProviderError`. Returns a `Completion` carrying tokens in, out and cached. |
| `fleet.py` | `ModelSpec` per tier: provider, model id, input and output price, measured quality, quality basis, latency, and whether it is serving. Loaded from `aml/llm/fleet.json`. `serving()` filters to the tiers the router may actually choose. |
| `router.py` | The **mechanism**: cheapest serving model that clears the quality floor, the rest of the chain held in reserve for failures, a spend cap (`BudgetExceeded`), and a ledger entry for every attempt including the failed ones. |

The fleet as configured:

| Tier | Model | Quality basis | Serving |
|---|---|---|---|
| rejected | `amazon.nova-lite-v1:0` | 3/8 escalation recall | no |
| cheap | `us.meta.llama3-3-70b-instruct-v1:0` | 6/8 escalation recall | yes |
| premium | `mistral.mistral-large-3-675b-instruct` | 8/8 escalation recall | yes |

Quality is a measured number with a date attached, not a vendor claim. A model
below the floor is in the file precisely so the refusal is visible.

---

## 5. `aml/security/` - the hostile surface

| Module | What it does |
|---|---|
| `envelope.py` | The untrusted-data envelope. Payment reference text is written by whoever sent the payment, and travels unmodified into the prompt - the one genuinely attacker-controlled surface. This wraps it in explicit delimiters with a preamble saying it is data, not instruction. |
| `injection.py` | The payload catalogue and the **deterministic** verdict on whether each one worked - a canary string, a disposition flip, a claimed action. Never asks another model whether it was attacked. |
| `paired.py` | Fires one payload twice: once with the reference text inline, once enveloped. Same alert, same model, same payload, same temperature. If one is hijacked and the other is not, the difference **is** the framing and cannot be anything else. |
| `swarm.py` | The sweep. Probes that can genuinely be run are run (`EXECUTED`); probes that describe a real risk the apparatus cannot execute are declared and say so (`DECLARED`). Nothing is reported as tested that was not tested. |
| `tools.py` | What the agent may do, and what **nothing** can grant it. `UNGRANTABLE` scopes - file a report, close a case, amend a party - raise `ScopeUngrantable` rather than `ToolDenied`. A compromised prompt, a persuaded operator and a bug all hit the same wall. |
| `emit.py` | What may leave the system. Two duties: telemetry must not carry identifiers that turn a metrics store into a copy of the customer master (`telemetry_safe`), and nothing the agent writes may disclose that a party is under suspicion (`guard_customer_text`, raising `TippingOff`) - a criminal offence, not a policy breach. |

---

## 6. `aml/core/` - the ledger

`ledger.py` is the single source of truth. Thread-safe. Two record types:

- **`CallRecord`** - one request to one model: tier, provider, model, tokens in
  / out / cached, cost, latency, status, attempt number, provenance.
- **`OutcomeRecord`** - what the agent decided about one alert and whether it
  was right.

From those it computes cost, groundedness, invented citations, model mix, cost
by tier, and cost per outcome. The economic overlay is held here and **labelled
as assumption, not measurement**:

| Constant | Value | What it is |
|---|---|---|
| `MANUAL_REVIEW_GBP` | 17.00 | 30 minutes of L1 analyst time, fully loaded |
| `PLATFORM_OVERHEAD_GBP` | 0.20 | storage, queueing and audit per disposition |
| `MISSED_SAR_GBP` | 85.00 | QA rework when a wrongly closed alert is sampled |
| `USD_TO_GBP` | 0.79 | |

Everything else in the ledger is computed.

---

## 7. `aml/improve/` - the improvement loop

| Module | What it does |
|---|---|
| `contract.py` | `ValueContract` - what the agent was funded to achieve. `INVESTIGATOR_CONTRACT`: GBP 17.00 baseline, GBP 12.00 target, 0.90 recall floor, 0.85 accuracy floor, approved by the Head of Financial Crime Technology. `require_contract()` raises `NoValueContract` rather than letting a run proceed without one. |
| `bands.py` | How far off target, in standard errors of the measurement itself. Band 1 / 2 / 3 map to what the agent is allowed to do about it. "Two sigma" means something specific about this corpus at this size, not a label someone chose. |
| `mining.py` | Clusters the failures and attributes a cause. Clustering uses **features visible in the alert**, never the label or the archetype that produced it - a cluster found by reading the answer key would not survive production. |
| `optimise.py` | Propose, evaluate, gate. `propose()` turns clusters into changes; `consensus()` runs the corpus repeatedly to separate signal from model variance; `evaluate()` scores a proposal against the same baseline on the same alerts; `sign_test()` is the paired statistic; `review()` is the gate that can and does refuse. |
| `tokenomics.py` | The same loop applied to spend. Finds the clusters of cost, prices each lever, and puts them to the same gate. One lever is the trap: dramatically cheaper, and refused, because the quality bar does not move to make a number look good. |
| `live.py` | `ab_live()` - the watchable version. The full evaluation is 70 alerts, three repeats, per configuration; this runs one proposal on the handful of alerts that provoked it, concurrently, so a decision can be seen being made. |

---

## 8. Data and configuration assets

| Path | What it is |
|---|---|
| `AntiMoneyLaundering/Alert_Final_table.xlsx` | The source extract: 35 alerts, 828 transaction rows, 25 parties, 25 filed reports. |
| `Actimize AML SAM 8.5.0 Solution Guide.pdf` | 677 pages, product confidential. The source of every threshold. |
| `library/aml/rules.json` | 28 extracted rule specifications across 4 detection models (AML-STR, AML-ECT, AML-EBB, AML-MLT), each with its page number, plus the 6 scenario codes mapped onto them. |
| `aml/llm/fleet.json` | The model fleet, prices and measured quality. |
| `artifacts/corpus.json` | The built 70-alert corpus, cached. |
| `artifacts/run_*.json` | Recorded baseline, attack and improvement runs. |

---

## 9. Entry points

Four scripts. Each one writes its evidence to `artifacts/` so a claim can be
checked later rather than taken on trust.

| Script | What it does |
|---|---|
| `scripts/build_rule_catalogue.py` | Extracts the in-scope Actimize rule specifications from the Solution Guide into `library/aml/rules.json`, with the page each came from. Run when the source document changes. |
| `scripts/run_baseline.py` | Runs the whole corpus on each serving tier and records the baseline. What the agent does before anything is improved. |
| `scripts/run_attacks.py` | Fires the swarm at the agent with the envelope off, then on. Same payloads, same alert, same model. |
| `scripts/run_improve.py` | The full loop: detect the deviation, mine the failures, propose with evidence, evaluate on the same corpus, gate every change, measure the contract again. |

All run with `uv run python scripts/<name>.py`. Bedrock credentials are read
from the local AWS configuration; nothing in the repo holds a secret.

---

## 10. The three things enforced in code

Worth knowing where they live, because they are the answer to the first three
questions any reviewer asks.

1. **The agent cannot file, close or amend anything.** `aml/security/tools.py`,
   `UNGRANTABLE`. Not an ungranted permission - an unavailable one.
2. **A citation is checked, not trusted.** `aml/run/verdict.py` and
   `check_evidence()` in `aml/run/routing.py`. An invented reference is a fact
   about the text, not a judgement.
3. **Nothing the agent writes may disclose suspicion.**
   `aml/security/emit.py`, `guard_customer_text()`.
