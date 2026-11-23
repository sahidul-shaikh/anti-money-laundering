# 03 — How it is built

## Package map

```
aml/
├── corpus/      the 70 alerts: load, synthesise, render
├── run/         the investigator: config, prompts, rules, routing, engine,
│                verdict, telemetry, chat
├── llm/         the fleet, Bedrock, the router
├── security/    envelope, injection payloads, paired probes, swarm, scopes, emit
├── improve/     contract, bands, mining, optimise, tokenomics, live A/B
├── build/       the twelve-stage factory and the act-verify-iterate loop
└── core/        the ledger

scripts/
├── serve_factory.py      the console server and its API (stdlib only)
├── ui/                   the console: factory.html, factory.js, panels.js, …
├── run_baseline.py       whole corpus on each serving tier
├── run_attacks.py        the swarm, envelope off then on
├── run_improve.py        detect, mine, propose, evaluate, gate
├── run_build.py          the twelve-stage factory end to end
└── build_rule_catalogue.py   extract rules from the Solution Guide

library/aml/     13 reusable skills + 19 pattern assets + rules.json
checks/          five pillar checks + the withheld acceptance suite
artifacts/       corpus, recorded runs, the generated detector
design/          26 documents: the production design for this product
docs/            runbooks, use case, architecture, repo map
```

**Dependency direction:** everything may use `core`; `corpus` and `llm` know
nothing of `run`; `improve` sits on top of all of it.

---

## The path of one alert

```
Alert
  → render()                  the investigator's view — no label, no rationale
  → rules.for_scenario()      the rule that fired, with its page citation
  → user_turn()               the message
  → system_prompt(config)     the standing instructions
  → Router.complete()         cheapest serving model above the quality floor
  → parse()                   Verdict: disposition, reasoning, citations
  → check_evidence()          every citation resolved against the alert
       ├─ grounded      → accept
       └─ not grounded  → escalate once to premium, then accept
  → grade()                   correct? cited? invented anything?
  → Ledger.record()           one call record, one outcome record
```

### The modules that matter most

| Module | What it does | Why it is the way it is |
|---|---|---|
| `corpus/render.py` | Turns an alert into what the model sees | **Carries no label and no rationale.** Anything the harness scores against must be absent here or the measurement is worthless |
| `run/rules.py` | Retrieves the rule in force by scenario code | Replaces prose a person transcribed with a citation to a page |
| `run/routing.py` | The *policy* — what to do when a cheap model answers but cannot show its working | On the recorded baseline the cheap tier returned no citable evidence on 12 of 61 clean alerts and was wrong on 67% of those against a 22% base rate. "Answered with nothing to point at" is a real signal |
| `run/verdict.py` | Parse and grade | **Groundedness is computed, not judged.** A cited reference either appears in the alert or it does not. No second model is involved |
| `llm/router.py` | The *mechanism* — cheapest serving model, fallback, spend cap, ledger entry per attempt | Mechanism and policy are deliberately separate modules |
| `security/envelope.py` | Wraps attacker-controlled text as data, not instruction | Applied in one render path so it cannot be bypassed by ad-hoc prompt assembly |
| `security/tools.py` | `UNGRANTABLE` scopes | Not a denied permission — an unavailable one. Raises at **registration**, not at call time |
| `improve/bands.py` | Deviation in standard errors, with tiered permitted actions | Band 1 autonomous, band 2 needs approval, band 3 halts. Autonomy *decreases* with severity, deliberately |
| `core/ledger.py` | Every call, every outcome, written once | The single source of every figure |

---

## The model fleet

`aml/llm/fleet.json`:

| Tier | Model | Measured quality | Serving |
|---|---|---|---|
| rejected | `amazon.nova-lite-v1:0` | 3/8 escalation recall | **no** |
| cheap | `us.meta.llama3-3-70b-instruct-v1:0` | 6/8 | yes |
| premium | `mistral.mistral-large-3-675b-instruct` | 8/8 | yes |

Quality is a measured number with a date attached, not a vendor claim. The
rejected model stays in the file **so the refusal is visible and re-testable**.

All inference goes through Amazon Bedrock Converse. Credentials are already
configured on this machine; nothing in the repo holds a secret.

---

## The build factory

`aml/build/` runs twelve governed stages — value contract, specification,
threat model, architecture, agent graph, context and skills, implementation,
code review, remediation, unit test, functional test, deployment and
observability. Each stage:

1. is a headless Claude Code call (`aml/build/claude_code.py`);
2. inherits reusable skills from `library/aml/skills/`;
3. is evaluated by `aml/build/evaluator.py` before the next stage starts.

The **implementation** stage adds the act-verify-iterate loop
(`aml/build/loop.py`, `aml/build/code.py`): generate, run a committed
acceptance suite the model never sees, feed the failure back, bounded at three
attempts.

Two details in that loop were hard-won and are worth not undoing:

- The feedback carries **the code the previous attempt wrote**, not just the
  pytest output. Without it the model rewrites from memory and sometimes
  produces something worse.
- The feedback carries **the pass count** — *19 of 20 already pass, change only
  what failed*. Without it attempt 2 trades one failure for another.

Both corrections were to what the verifier tells the builder, not to the
builder.

---

## The console

`scripts/serve_factory.py` is a standard-library HTTP server that serves the UI
and exposes the API the panels call. Serving the page from the same origin as
the API is why no CORS arrangement is needed.

- `scripts/ui/factory.html` — the shell
- `scripts/ui/factory.js` — routing and the `F.register(pillar, panel, fn)` API
- `scripts/ui/panels.js` — most live panels
- `scripts/ui/builds.js`, `runs.js`, `secures.js`, `improves.js` — pillar panels
- `scripts/ui/factory.css` — Accenture house style

**Panel host element is `#dpanel`, not `#view`.** A panel registers itself and
renders into that host.

> Note: some panels in `builds.js` / `runs.js` / `secures.js` / `improves.js`
> have been superseded by `panels.js` and are dead code. `fleetTable` in
> `runs.js` is also unused. Clearing that is a reasonable first warm-up task.
