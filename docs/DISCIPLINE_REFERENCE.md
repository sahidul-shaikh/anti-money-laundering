# Discipline reference

The console carries a one-line claim per discipline. Timings, costs and the
reasoning behind each claim are here.

| Press | Where | Takes | Costs |
|---|---|---|---|
| stage 0: read it | Builds / Specs | ~12s | $0.05 |
| run this stage live | Builds / Context | 45-90s | ~$0.06 |
| run the implementation stage | Builds / Loops | ~2min on haiku, fails then passes | $0.01-0.02 |
| run the tests | Builds / Evaluation | ~30s | nothing |
| start | Runs / Routing | 10-25s | ~$0.006 |
| send it | Runs / Reliability | 20-40s | ~$0.003 |
| send both to the agent | Secures / Pen-testing | ~16s | ~$0.002 |
| walk through it | Improves / Harness | ~40s, five cards | ~$0.004 |
| run the cache probe | Improves / Tokenomics | ~25s, 5 calls | negligible |

The whole demo is roughly **$0.80**, nearly all of it in the Builds loop.

## AI builds AI

*From individual craftsmanship into a repeatable AI engineering factory.*

### 01 Specs

**One human writes the requirement. Nothing downstream is hardcoded.**

A human-authored requirements document is the only input to the factory. Stage 0 reads it with Claude Code and extracts a structured brief; a human approves that brief; every one of the twelve stages is then handed it. Change the document, re-read it, and the whole factory changes with it.

> The brief is extracted by a model but approved by a person. The approval is the control.

In the repo: `PRD.md`, `aml/build/brief.py`

### 02 Context

**Each stage is sent a precise, auditable context window - readable before it runs.**

A stage prompt is assembled from five parts: the standing preamble, the approved brief, the artifacts its upstream stages produced, the skills it declares, and its own instruction. Nothing else reaches the model. You can read the exact characters without spending anything.

> Context is composed, not accumulated. A stage cannot see what it does not depend on.

In the repo: `aml/build/orchestrator.py`

### 03 Skills

**Procedural knowledge is a reusable file on disk, not a prompt someone remembers.**

Thirteen skill files encode how each discipline is done - what good looks like, and the specific mistakes that have been made before. Each stage declares the skills it needs and they are inlined into its prompt under HOW THIS DISCIPLINE IS DONE. The skills outlive the build that produced them.

> This is the compounding asset. The code is specific to one product; the way of working is not.

In the repo: `library/aml/skills/`

### 04 Loops

**Goal, act, verify, iterate - against a contract the model cannot see.**

The implementation stage writes a module and its tests, then an independent acceptance suite runs them. A failure is not reported, it is fed back as the next instruction. Three attempts, and then the gate says no.

> Withhold the rule detail and the first attempt fails every time - the suite requires an output convention the brief does not state, and nothing can infer it. Give the stage the full requirements and it passes first time. The loop, not the model, is what closes the gap.

In the repo: `aml/build/loop.py`, `aml/build/code.py`

### 05 Graphs

**Twelve stages, fifteen dependencies, four gates. Enforced, not drawn.**

Every stage declares what it depends on. The orchestrator walks that graph, forks where work is independent and joins where evidence has to be assembled, and refuses to start a stage whose upstream has not passed. Four stages are gated and stop for a human.

> The joins are the interesting part: model risk cannot run until evaluation, security review and code review have all produced evidence.

In the repo: `aml/build/phases.py`, `aml/build/orchestrator.py`

### 06 Evaluation

**Break a stage's output on purpose and watch the gate refuse it.**

Documents must carry their required sections as real headings, not as a phrase buried in a paragraph. Code is judged by nineteen acceptance tests that are committed before the build and never shown to the model. Tamper with either and press re-evaluate.

> The oracle is written first and withheld. That is the difference between evaluation and self-assessment.

In the repo: `aml/build/evaluator.py`, `checks/acceptance/test_detector_contract.py`

## AI runs AI

*A self-operating estate: AI takes over the routine operations.*

### 01 Routing

**Try the cheap model first. Trust its answer only if it can point at the transactions. Escalate if it cannot.**

One real call to Amazon Bedrock, in front of you. The policy starts at the cheapest model above the declared quality floor, then checks the answer against the alert's own transaction list. An answer that cites nothing, or cites a reference the alert does not contain, is not trusted and the alert is escalated to the stronger model. On the recorded corpus that policy beats both flat tiers on accuracy and recall at 85 percent of premium's spend.

> The escalation trigger is computed, not judged. No model is asked whether the answer was any good - every cited reference is ticked off against the alert.

In the repo: `aml/run/routing.py`, `aml/llm/router.py`, `aml/llm/fleet.json`

### 02 Reliability

**A failed call is not a wrong answer, and must not be priced as one.**

Point a tier at a model that does not exist and the call genuinely fails at Bedrock. The router records the failed attempt and moves to the next eligible model, so the alert is still dispositioned. Where no model answers, the outcome is PROVIDER_ERROR - a distinct disposition, surfaced in telemetry and priced at the cost of a human review, never as a missed report.

> The first full run reported 52 of 70 alerts unparseable. It was Bedrock throttling, not model quality. Adaptive retry took accuracy from 17.1 to 57.1 percent.

In the repo: `aml/llm/router.py`, `aml/llm/bedrock.py`, `aml/core/ledger.py`

### 03 Observability

**Uptime and error rate answer none of the questions a regulator asks about an AI control.**

Five layers, recorded for every run: SYSTEM (availability, latency, provider errors), MODEL (tokens, spend, model mix), AGENT (groundedness, invented citations, unparseable answers, confidence), TRANSACTION (accuracy, recall, specificity, and accuracy per scenario), and VALUE (cost per outcome against the manual baseline).

> Scenario SAS10050 scores 53.6 percent accuracy against 93.8 for SAS10014. An aggregate number would have hidden that entirely.

In the repo: `aml/run/telemetry.py`, `artifacts/run_baseline.json`

### 04 FinOps

**Token spend is not the cost. Cost per correctly handled alert is the cost.**

Every call is priced from the AWS Price List API and written to a ledger. The number that matters is cost per outcome in pounds - model spend plus the human handling each disposition implies, where a missed escalation costs far more than a review. Measured against a 17.00 pound manual baseline and a 12.00 pound contractual target.

> At launch the agent costs MORE than the analyst it replaces - 18.77 pounds against 17.00. That is measured, not hidden, and it is what the Improve pillar has to close.

In the repo: `aml/core/ledger.py`, `aml/llm/fleet.py`, `aml/improve/tokenomics.py`

## AI secures AI

*Security is engineered into every stage and continuously hardened by learning.*

### 01 Threat modelling

**The threats are named before the build, by the stage that cannot proceed without naming them.**

Stage 2 of the factory cannot pass its evaluator unless it produces a THREAT MODEL section carrying identified threats. The threat library it works from is a skill file on disk, so the next product inherits it rather than rediscovering it. Nine threats are named for this product, each with a control and a residual risk.

> This is not a document someone wrote afterwards. The build gate would have blocked without it, and you can prove that in the Builds pillar by renaming the heading.

In the repo: `library/aml/skills/threat-modelling.md`, `artifacts/builds/aml-alert-investigator/spec.md`

### 02 Runtime defense

**Untrusted text is not filtered. It is labelled, so it arrives as evidence rather than as an instruction.**

A filter has to recognise an attack, which is a losing game against anyone who can rephrase. The envelope does not try: it wraps text written by outsiders in a label that says who wrote it and what it is for. Alongside it sit six capabilities defined as ungrantable - a request for one raises rather than returning a token, so no amount of persuasion reaches them.

> The agent has no tools today, so the ungrantable scopes guard nothing yet. They are the right shape for when tools arrive, and P-05 tests the thing that is reachable: whether the agent falsely claims to have acted.

In the repo: `aml/security/envelope.py`, `aml/security/tools.py`

### 03 Pen-testing

**An attacker writes into the one field they control. Unprotected it works; framed as untrusted text it does not.**

Five injection payloads with deterministic judges - a regex or a disposition comparison, never a model asked for its opinion. Three controls that need no model at all. Two probes declared but not executed, because the apparatus to run them honestly does not exist here. Anything that looks exploited is fired again before it is believed, and anything that does not reproduce is discarded rather than published.

> One finding in the recorded sweep did not reproduce on re-run and was thrown away. A pen test that only reports hits is marketing.

In the repo: `aml/security/swarm.py`, `aml/security/tools.py`, `artifacts/run_attacks.json`

## AI improves AI

*Every production cycle makes the AI estate measurably better.*

### 01 Harness

**One mistake, one fix, and the same alert answered again.**

The same configuration run twice on this corpus moves several accuracy points and flips six of seventy alerts. So changes are judged on a paired per-alert comparison with a two-sided sign test, not on an aggregate percentage, and every configuration is run more than once with the per-alert majority taken. Pick a proposal and watch it measured live against the alerts that provoked it.

> The live subset shows the mechanism, not the statistics. A dozen alerts cannot produce the six one-way flips significance needs - and the gate says so rather than pretending.

In the repo: `aml/improve/optimise.py`, `aml/improve/live.py`

### 02 Failure mining

**The same mistake, made repeatedly, grouped by what the alert looks like.**

Failures are clustered on observable features - the shape of the activity, the party type, how many sibling alerts exist - because a cluster built on the label is circular and tells you nothing you can act on. A cluster is only reported above a materiality floor: the miner declines to change a regulated control on the evidence of two examples.

> One cluster has no attributed cause and says so. Three missed escalations on unremarkable-looking activity is a finding for an analyst, not a prompt change.

In the repo: `aml/improve/mining.py`, `artifacts/run_improve.json`

### 03 Tokenomics

**The instructions every call carries, measured and then made smaller.**

Four spend clusters mined from the token ledger, each with a measured share and a costed lever. Two were refused on measurement - routing everything to the cheap tier costs 14.3 accuracy points, and the cheapest model in the fleet misses most suspicious activity. The fixed instruction prefix is 47 percent of input spend and is measured live, here, with two real calls.

> The obvious saving is the one the gate refused. A cost proposal carries the burden of showing quality was kept - the quality bar does not move to let it through.

In the repo: `aml/improve/tokenomics.py`, `aml/core/ledger.py`

### 04 Value engineering

**A target set before the build, and how far short we still are.**

The value contract is declared before the build: a baseline, a target, a binding recall floor and an accuracy floor. Distance from target is reported in standard errors computed from the measurement itself, so a gap that is within noise is not dressed up as progress. After the approved change the contract is still not met, and the console says by how much.

> Sigma is arithmetic, not a label. A two-sigma gap is a gap; a half-sigma gap is a measurement you cannot act on yet.

In the repo: `aml/improve/contract.py`, `aml/improve/bands.py`
