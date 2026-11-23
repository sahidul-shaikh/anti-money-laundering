# Demo runbook - AI runs AI

How to operate the second pillar. Every figure here was measured on this
machine; the live timings come from calls made through the console itself.

Companion to [DEMO_RUNBOOK_BUILDS.md](DEMO_RUNBOOK_BUILDS.md) (Builds) and
[DEMO_RUNBOOK_SECURES.md](DEMO_RUNBOOK_SECURES.md) (Secures). Same server, same
console, same startup.

**Before the console.** [USE_CASE.md](USE_CASE.md) is the problem, the data and
what we are claiming - read it first if you have not presented this before.
[ARCHITECTURE.md](ARCHITECTURE.md) is how the product is put together, for the
engineer in the room who asks.

---

## 1. Before the room arrives

### Start the server

```
cd "C:\Users\sahidul.i.shaikh\OneDrive - Accenture\Documents\Project\AI_For_AI"
uv run python scripts/serve_factory.py
```

Open **<http://localhost:8765>** and click **AI runs AI** in the top nav.

If the port is stuck, see the recovery section of the Builds runbook - the
PowerShell `Get-NetTCPConnection` incantation is the same.

### Pre-flight, two minutes

1. Top right reads **live** with a green dot.
2. **01 Routing** → press **route this alert** on the default alert. It must
   complete in under 20 seconds and finish **CORRECT**. This is the only
   pre-flight that matters; it exercises AWS credentials, the Bedrock region,
   both models, the parser and the evidence check in one press.
3. **03 Observability** must show two tiers of telemetry. If it is empty,
   `artifacts/run_baseline.json` is missing.

> This pillar calls **Amazon Bedrock**, not Claude Code. If routing fails but the
> Builds pillar works, the problem is AWS credentials, not the console.

### What it costs

About **$0.01** to run every live beat once. Routing is ~$0.0064 per press,
Reliability ~$0.0029. You can rehearse this pillar twenty times for the price of
a single Builds loop.

---

## 2. Where you run things

| What | Where | How long | Cost |
|---|---|---|---|
| **Route one alert for real** | **01 Routing** → *route this alert* | 6-20s | ~$0.0064 |
| **Break a tier and watch the fallback** | **02 Reliability** → *route it* | 6-10s | ~$0.0029 |
| Observability | nothing to run - recorded | - | - |
| FinOps | nothing to run - recorded | - | - |

Two of the four disciplines are live and two read the measured baseline. The
console badges each one `live` or `recorded`, so you never have to claim
otherwise.

---

## 3. The run of show

### 01 Routing - the beat of this pillar

The panel runs as a workflow, one step appearing at a time. Press **start** and
narrate as each card lands.

**Step 1 - ask the cheap model.** Every alert starts here; there is no model
picker. The card shows what it said, how many transactions it cited, and the
rule that was read from the rulebook with its page number. On alert 11368 it
closes the alert citing nothing, and the card is marked **NOT GOOD ENOUGH**.

**Step 2 - escalate.** The cheap answer could not be checked against the alert,
so the policy sends the same alert to the stronger model. Say the important
part: *nothing about the alert changed - only which model was asked.*

**Step 3 - ask the premium model.** It escalates the alert and cites the
transactions that justify it. Marked **GOOD ENOUGH**.

**Outcome.** The disposition, whether it was right, and which model decided it.

The line to land: the cheap model was not overruled for being cheap. It was
overruled because it could not point at the evidence.

### 02 Reliability - a failed call is not a bad answer

**What the panel actually does.** Pressing send hands the router a model id
that does not exist, in place of the one the cheap tier really calls. The
request still goes to Bedrock, and Bedrock is what refuses it. The result block
names both ids, so the audience can see for themselves that the only thing
changed was a string:

```
The cheap tier really calls   us.meta.llama3-3-70b-instruct-v1:0     exists
This run asked for            meta.llama3-3-70b-instruct-v9:0        no such model
Bedrock replied               ValidationException: The provided model
                              identifier is invalid.                 CALL FAILED
```

Be straight that this is **fault injection standing in for an outage** - the
failure that actually happened in the recorded run was throttling, which cannot
be reproduced on demand. What is real either way: the router cannot tell the
difference. Press **send it** and one result block comes back: the cheap call
marked **CALL FAILED** with the provider's own error text, then the
disposition and which tier reached it, and under that the stronger model's own
answer - its narrative, the transactions it cited, and the full reply behind a
link. The alert is still dispositioned at the end.

Where nothing answers at all, the outcome is a provider error: queued to a
human and priced as a review, never as a missed report.

### 03 Observability - five layers

Nothing to press. Walk down it:

- **SYSTEM** - availability, latency, provider errors. Necessary, nowhere near
  sufficient.
- **MODEL** - 84,237 / 116,301 input tokens, spend, model mix.
- **AGENT** - cheap groundedness **0.700** against premium's **0.998**; 335 vs
  670 citations; mean confidence 0.766 vs 0.904. The cheap tier is both less
  grounded *and* less willing to show its working.
- **TRANSACTION** - accuracy, recall, specificity, and accuracy per scenario.
- **VALUE** - cost per outcome against the £17.00 baseline, and the saving as a
  negative number.

Then the scenario table, which is the point of the panel:

| Scenario | Alerts | Accuracy |
|---|---|---|
| SAS10602 | 2 | 50.0% |
| SAS10050 | 28 | 53.6% |
| SAS10056 | 18 | 83.3% |
| SAS10014 | 16 | 93.8% |
| SAS10012 | 2 | 100.0% |
| SAS10016 | 4 | 100.0% |

Same agent, same prompt, same run, a 40-point spread. An aggregate accuracy of
74.3% would have hidden all of it. **SAS10050 is 28 of the 61 alerts and the
worst performer** - that is where the next piece of work is, and the telemetry
found it, not an opinion.

### 04 FinOps - cost per outcome, not cost per token

1. The per-tier table, ending in the **vs £17 manual** column: cheap −£6.85,
   premium −£1.77. **At launch the agent costs more than the analyst it is meant
   to relieve.** Say it plainly; it is measured and it is on screen.
2. **Where the money actually goes** - four spend clusters from the token ledger,
   each with a verdict. Two were refused:
   - **TOK-03, route everything to the cheap tier** → *REFUSE: accuracy falls
     14.3% (74.3% to 60.0%)*
   - **TOK-04, use the cheaper model outside the fleet** → *REFUSE: 38% recall
     means it misses most suspicious activity*
   - TOK-01, cache the 786-token prefix (47.3% of input spend) → costed and left
     open, because neither serving model supports prompt caching.
3. **The tie-back.** TOK-03 is the naive version of discipline 01 and it was
   refused on measurement. Evidence-gated routing is what that refusal forced:
   escalate only the answers you cannot verify, and you get better accuracy than
   premium for 85% of its spend. *Routing is not a cost optimisation that cost
   accuracy. It is the one that did not.*

### Close the pillar

Press **Next: AI secures AI** - that pillar is in this console now, and its
runbook is [DEMO_RUNBOOK_SECURES.md](DEMO_RUNBOOK_SECURES.md).

---

## 4. Honest caveats

### The corpus-wide routing table is a counterfactual

Both tiers answered every alert in the recorded baseline, so the evidence-gated
row is **arithmetic on measured data** - not a separate run of the policy. The
console says so on the card. If asked whether the policy has been run end to end
over all 70: it has not. Each individual alert routed in the panel is fully real;
the aggregate is recomputed. Closing that gap is one real run of about $0.10.

### The live call may not reproduce the recorded failure

The noise floor is **6 of 70 alerts flip on an identical rerun**. Alert 11368 has
reproduced its failure every time it has been routed here, but it is not
guaranteed.

This does not matter, and the framing is why: **the beat is the control working,
not the model failing.** If the cheap answer cites nothing, you watch the policy
escalate. If the cheap answer is good and verifiable, the policy accepts it and
you have shown the cheap path doing the job for a tenth of a cent. Both outcomes
prove the design. Never say "watch it get this wrong" - say "watch what the
policy does with the answer".

### Nine alerts are excluded from the comparison

Any alert where either tier hit a provider error is dropped from the routing
table, because a call that never reached a model is not a bad answer. That is
stated on the card and it is why the table says 61 and not 70.

### The invented-reference trigger never fires on this corpus

The policy escalates on *no citations* or *a citation not in the alert*. On the
recorded baseline the cheap tier **never invented a reference** - when it was
ungrounded it was because it cited nothing at all. The second clause is real code
and it is dead on this data. If someone asks, say that; do not claim a signal the
corpus does not show.

### Two tiers, one estate - and no Claude on Bedrock

`cheap` is Llama 3.3 70B, `premium` is Mistral Large 3, both via the Bedrock
Converse API in us-east-1. There is no Anthropic model in this fleet because the
AWS account has no payment instrument, so the Marketplace subscription cannot
complete. The Builds pillar runs on Claude Code on a subscription - a different
estate entirely, and the costs are not comparable.

---

## 5. What this hands to AI improves AI

Worth saying at the end of the pillar, because it sets up the next one. Nothing
here is staged - all three gaps are measured and visible on the console:

1. **Cost is above the baseline.** £17.89 routed, £21.23 premium, against £17.00
   manual and a £12.00 target.
2. **Recall is below the binding constraint.** 85.7% against 90%.
3. **One scenario carries the failure.** SAS10050, 28 alerts, 53.6% accuracy.

And routing adds a fourth thing that did not exist before: **the policy itself is
now a parameter** - the quality floor, the escalation trigger, how many
escalations are allowed. `aml/llm/router.py` says so in its own docstring, and it
was written before any of this:

> *"Smarter routing is a change the Improve pillar has to propose, measure and
> get approved - not something asserted here."*

---

## 6. Recovery

| Symptom | Cause | Fix |
|---|---|---|
| Routing says *could not start* | A route for that alert is still in flight | Wait, or pick a different alert |
| Every call errors immediately | AWS credentials expired | Refresh them; the Builds pillar will still work, which is the tell |
| `ValidationException` on a tier you did not break | Model id changed or access lapsed | Check `aml/llm/fleet.json` against the Bedrock console |
| Observability or FinOps empty | `artifacts/run_baseline.json` missing | `uv run python scripts/run_baseline.py` (~9 min, $0.20) |
| Spend clusters empty | `artifacts/run_improve.json` missing | `uv run python scripts/run_improve.py` (~15 min, $0.50) |
| Routing panel shows no candidates | Baseline missing, so nothing is flagged | Untick *only alerts the cheap tier got wrong* |

Nothing in this pillar writes to the repo, so there is no tamper to undo and no
backup to restore. The only side effect of a live route is a few tenths of a cent
and a ledger entry held in memory.

### Verify the pillar

```
uv run python checks/aml_check_01_run.py
```

All five `aml_check_0*.py` currently pass.

---

## 7. Files

```
aml/run/routing.py        the policy: evidence check, escalation, fault injection
aml/llm/router.py         the mechanism: quality floor, fallback, spend cap, ledger
aml/llm/fleet.json        the two serving tiers and the withdrawn one
scripts/ui/runs.js        the four panels
library/pillars.json      the pillar and discipline copy
```

Server endpoints added for this pillar:

| Endpoint | Returns |
|---|---|
| `GET /api/alerts` | all 70 alerts, with the recorded outcome per tier and a `candidate` flag |
| `GET /api/runs/recorded` | summaries, five-layer telemetry, spend clusters, fleet, the counterfactual |
| `POST /api/route/<alert_id>` | start a live route; body sets the quality floor, the gate, and `break_tier` |
| `GET /api/routestream/<alert_id>` | the route as it happens |
