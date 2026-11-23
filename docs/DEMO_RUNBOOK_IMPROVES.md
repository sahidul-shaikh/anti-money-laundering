# Demo runbook - AI improves AI

How to operate the fourth and last pillar. Every figure here was measured on
this machine; the live timings come from an A/B run through the console itself.

Companion to [DEMO_RUNBOOK_BUILDS.md](DEMO_RUNBOOK_BUILDS.md) (Builds),
[DEMO_RUNBOOK_RUNS.md](DEMO_RUNBOOK_RUNS.md) (Runs) and
[DEMO_RUNBOOK_SECURES.md](DEMO_RUNBOOK_SECURES.md) (Secures).

**Before the console.** [USE_CASE.md](USE_CASE.md) is the problem, the data and
what we are claiming - read it first if you have not presented this before.
[ARCHITECTURE.md](ARCHITECTURE.md) is how the product is put together, for the
engineer in the room who asks.

---

## 1. Before the room arrives

Start the server, open **<http://localhost:8765>**, click **AI improves AI**.

### Pre-flight

1. Top right reads **live**.
2. **03 Tokenomics** → press **measure it now**. Two real calls, a second or
   two, and it must return **549 tokens**. Cheapest possible proof that Bedrock
   is reachable.
3. **01 Harness** must offer `ACC-01 · explain_before_escalate (12 alerts)` in
   the dropdown. If it offers nothing, `artifacts/run_improve.json` is missing.

### What it costs

About **$0.05** for the whole pillar: $0.046 for the live A/B, effectively
nothing for the token measurement. Budget **40 seconds** for the A/B.

---

## 2. Where you run things

| What | Where | How long | Cost |
|---|---|---|---|
| **Measure a proposed change, before and after** | **01 Harness** → *measure it* | ~36s | $0.046 |
| **One case, before and after** | **01 Harness** → *run it both ways* | ~20s | $0.004 |
| **Price the system prefix** | **03 Tokenomics** → *measure it now* | ~2s | ~$0 |
| Failure mining | nothing to run - recorded | - | - |
| Value engineering | nothing to run - recorded | - | - |

---

## 3. The run of show

### 01 Harness - one alert, read in public

Pick **S90009** and press **walk through it**. Five cards land in order, about
forty seconds, two real calls. Narrate them as they arrive.

**Step 1 - what the agent was looking at.** Thomas Brennan, a serving soldier,
declared income $68,900. Five transactions, and they are on the screen:

| Date | Reference | Amount | Direction |
|---|---|---|---|
| 26 Aug 2018 | 2000000039 | $3,960.00 | CREDIT |
| 26 Sep 2018 | 2000000040 | $3,960.00 | CREDIT |
| 26 Oct 2018 | 2000000041 | $3,960.00 | CREDIT |
| 26 Nov 2018 | 2000000042 | $3,960.00 | CREDIT |
| 28 Nov 2018 | 2000000043 | $12,672.00 | DEBIT |

Let the room read it. Four identical credits on the 26th of each month is a
salary, and the $12,672 payment two days after the fourth one is what the
salary paid for. **show the whole prompt the agent was sent** opens the exact
user turn behind the card - the rule that fired with its page citation, the
party, the account and those five rows. Nothing is held back from the audience
that was not held back from the model.

**Step 2 - what it decided.** The right answer is *close, nothing to see*. The
agent escalated. Read its own words out loud; they are the point of the whole
pillar:

> a $12,672 debit (ref: 2000000043) exceeded the $10,000 daily threshold for
> high-risk instruments. This transaction was preceded by four monthly external
> transfers of $3,960 each (refs: 2000000039-2000000042), **suggesting
> potential layering or structuring of funds**.

It found the explanation, and then offered it as evidence against the man. A
soldier's pay became "potential layering".

**Step 3 - why.** It read value as suspicion and rhythm as concealment. The
declared income is in the same record and it never weighed it.

**Step 4 - the fix.** One block appended to the standing instructions, printed
exactly as the code holds it, not paraphrased. The base prompt is not edited -
additions go on the end, so the stable prefix stays stable. **show the standing
instructions with it applied** prints the whole thing.

**Step 5 - the same alert, again.** Same alert, same five rows, same model. It
closes it, and names what explained it: a single debit does not satisfy a
recurrence requirement, and the four credits are a salary consistent with
$68,900 of declared income.

Two other cases are in the dropdown and both tell the same shape of story: a
hardware shop's fortnightly supplier payments read as structuring, and a
$45,500 settlement cheque that was banked and never moved read as layering.

**If the before arm comes back right.** It happens, and the panel says so
rather than hiding it - the card is marked *RIGHT THIS TIME* and the status
line names it as run-to-run variance. That is not a broken demo, it is the
exact reason the table underneath exists. Say so and move to it.

#### Then the measurement that decides

The noise floor card is next. The same configuration, run twice, nothing altered
between the runs:

- **2 improved, 4 regressed**, p=0.688 - on a change of *nothing at all*
- accuracy moved **−2.9 points** by itself
- **6 of 70 alerts** disagree with themselves on a rerun

Say what that means: *a change that moved accuracy two points would be
indistinguishable from doing nothing.* This is why the gate uses a paired
per-alert sign test and not an aggregate percentage.

**Then press *measure it*.** `ACC-01 · explain_before_escalate` against the
twelve alerts its own failure clusters identified. 24 real calls, ~36 seconds.

What appears, in order:

| Panel | What it shows |
|---|---|
| **Plan** | The proposal, the rationale mined from the clusters, the evidence, and a warning: significance needs 6 one-way flips and this sample has 12 alerts. |
| **As configured today** | 1 of 12 correct. These are the alerts the miner flagged, so almost all are wrong by construction. |
| **With the change applied** | 5 of 12 correct. |
| **Paired, alert by alert** | Every alert, before and after, with the direction of each flip. |
| **The gate** | `insufficient_evidence`. |

The measured result:

```
S90009   wrong -> correct   improved
S90011   wrong -> correct   improved
S90013   wrong -> correct   improved
S90034   wrong -> correct   improved
(eight unchanged, none regressed)

4 improved, 0 regressed, p=0.125
accuracy +33.3 points, cost -5.60 GBP per outcome
$0.0414 over 12 alerts
```

**This is the line to land.** The change worked. Four alerts flipped the right
way, **zero** flipped the wrong way, accuracy rose 33 points on exactly the
failures it was designed for - **and the gate still refused to approve it.**
Four one-way flips give p=0.125; the bar is p<0.05, which needs six.

Then say why that is the right answer, not a bureaucratic one. Scroll to the
third card, the full 70-alert evaluation:

| Proposal | Change | Improved | Regressed | p | £/outcome | Gate |
|---|---|---|---|---|---|---|
| ACC-01 | explain_before_escalate | 7 | 6 | 1.000 | +1.45 | insufficient evidence |
| CST-01 | consolidate_by_party | 4 | 2 | 0.688 | −5.02 | **approved** |

On the full corpus the same change fixed 7 and broke 6. **It worked on the
cluster and broke other things elsewhere.** The gate that refused it on 12
alerts was protecting you from exactly that - and it did so before anyone had
seen the full result.

> `CST-01` is not offered in the live picker, and the console says why: it was
> mined from the token ledger rather than from a failure cluster, so there are
> no alerts that provoked it to measure it against.

### 02 Failure mining - diagnose before you prescribe

1. **12 failures, 15 clustered, 4 clusters, £510 sitting in them**, with a
   materiality floor of 3.
2. The key sentence: clusters are built on **observable features** - the shape of
   the activity, the party type, how many sibling alerts exist - and **never on
   the label**. A cluster built on the answer you already know is circular and
   gives an engineer nothing to change.
3. Walk the four clusters. Three over-escalation clusters each point at a
   concrete change. Then point at the fourth:

   > `missed_escalation:unremarkable` - 3 alerts, £306 - *"No attributed cause
   > yet; needs an analyst."*

   That is the most honest row on the page. Three missed escalations on activity
   that looks unremarkable is a finding for a human being, not a prompt tweak.
4. The materiality floor: a cluster below three examples is not reported at all.
   *The miner declines to change a regulated control on the evidence of two
   alerts.*

### 03 Tokenomics - one lever, asked rather than assumed

The agent carries the same 549 tokens of standing instruction into all seventy
alerts: 38,430 input tokens that never change. Bedrock will bill a repeated
prefix at a tenth of the rate - **if** the model supports prompt caching. Most
decks assert that saving. This one asks for it.

Press **run the cache probe**. It sends the real system prompt twice to every
model in the fleet, with a cache point in the request, and prints what came
back:

| Model | Tier | What Bedrock did |
|---|---|---|
| `amazon.nova-lite-v1:0` | not in service | wrote 540 tokens, then read 540 back |
| `us.meta.llama3-3-70b-instruct-v1:0` | cheap | `AccessDeniedException: You invoked an unsupported model or your request did not allow prompt caching` |
| `mistral.mistral-large-3-675b-instruct` | premium | the same refusal |

The mechanism is real and you watched it work: one model wrote the prefix to
cache and read it straight back. **38,430 tokens would become 3,843. Ninety per
cent off the fixed prefix.**

And we cannot have it. Both serving models refuse the request outright, and the
only model in the fleet that caches is the one the quality gate already
rejected. That makes this a procurement decision, not an engineering one - the
honest thing to carry out of the room, and more useful than a saving nobody
checked.

Say the size out loud too. Priced on the premium model, the whole fixed prefix
across seventy alerts is **$0.0192**, and $0.0019 cached. It is pennies. The
money in this process is the GBP 17.00 of human review per alert, which is what
the next panel is about.

The four spend clusters underneath carry the same discipline. Two were refused:
   - **TOK-03, route everything to the cheap tier** → *REFUSE: accuracy falls
     14.3% (74.3% to 60.0%)*
   - **TOK-04, use the cheaper model outside the fleet** → *REFUSE: 38% recall
     means it misses most suspicious activity*
3. **TOK-01**, the fixed prefix, was 47.3% of input spend. Part of it has now
   been removed outright by the rule catalogue; the remaining lever is prompt
   caching, and *neither serving model supports it*, so that part stays costed
   and open rather than claimed as a saving.
4. The line: **the obvious saving is the one that was refused.** A cost proposal
   carries the burden of proving quality was kept. The quality bar does not move
   to let it through.

### 04 Value engineering - the verdict

1. **The contract**, declared before the build: £17.00 baseline, £12.00 target,
   90% binding recall floor, 85% accuracy floor, approved by the Head of
   Financial Crime Technology.
2. **How far off, in standard errors.** Not adjectives:

   | Metric | Observed | Target | Std error | Sigma |
   |---|---|---|---|---|
   | accuracy | 0.7429 | 0.8500 | 0.0522 | 2.05 |
   | recall | 0.8286 | 0.9000 | 0.0637 | 1.12 |
   | cost per outcome | 18.77 | 12.00 | 3.21 | 2.11 |

   Sigma is computed from the measurement's own standard error. Recall at 1.12
   sigma is a real gap but a weak one; accuracy and cost at ~2 sigma are gaps you
   can act on. *A half-sigma gap is a number you cannot act on yet.*
3. **Where it actually landed.** All three targets **not met**:

   | Target | Achieved | |
   |---|---|---|
   | ≤ £12.00 per outcome | £15.12 | not met |
   | ≥ 90.0% recall | 83.8% | not met |
   | ≥ 85.0% accuracy | 74.8% | not met |

   **37.5% of the cost gap closed, 1 change approved, 1 held back.**

4. Close the demo on that. *One improvement cycle closed just over a third of the
   cost gap. The contract is not met, the console says so, and nothing here
   found a number that looked better.*

---

## 4. Honest caveats

### The live A/B cannot reach significance, and says so

Twelve alerts cannot produce the six one-way flips a two-sided sign test needs
at p<0.05. The plan card states this before the run starts. What the live run
demonstrates is the **mechanism** - mine a failure, propose a change, run the
same alerts both ways, pair them, test the direction of the flips, and let a
tri-state gate rule. The **statistics** come from the recorded 70-alert,
three-repeat evaluation shown underneath.

Do not say "watch it prove the change works". Say "watch it measure the change,
and watch the gate refuse to be convinced".

### The live subset is one run, not a consensus

The dropdown defaults to **1 run each**. The recorded evaluation uses three runs
per configuration with a per-alert majority, which is what cut unstable alerts
from 6 to 3. You can set the live run to 2, which doubles the time and cost. At
1 run, the noise floor applies to the live result too - and given 4-0 in one
direction, that is worth saying out loud rather than hiding.

### The before arm is 1 of 12 by construction

These twelve alerts were *selected because the agent got them wrong*. The before
arm is not a fair baseline for the product - it is the diagnostic set. The fair
baseline is the 70-alert number in the third card. If someone asks "so accuracy
is 8%?", that is the answer.

### The improvement loop is not autonomous

A model did not propose these changes. The clusters are computed by
`mining.py` from observable features; the proposals are generated by `propose()`
from a fixed map of cluster signature to config flag; the gate is arithmetic. The
"AI" in this pillar is the agent being measured, not an agent doing the
measuring. That is a deliberate choice for a regulated control, and it is worth
stating before anyone assumes otherwise.

### Only four config flags exist

`explain_before_escalate`, `evidence_for_close`, `consolidate_by_party`,
`compress_context`. The improvement space is those four switches and the routing
policy from the Runs pillar - not an open-ended search. A change outside that set
needs a human to write it.

---

## 5. Recovery

Nothing in this pillar writes to the repo.

| Symptom | Cause | Fix |
|---|---|---|
| Dropdown empty | `artifacts/run_improve.json` missing | `uv run python scripts/run_improve.py` (~15 min, $0.50) |
| *could not start - one may be running* | One A/B at a time | Wait for it |
| Token measurement fails | AWS credentials | Refresh them |
| Live A/B result differs from this guide | Expected - 1 run, and the noise floor is 6 of 70 | Say so; the direction has been stable across runs |

```
uv run python checks/aml_check_03_improve.py
```

All five `aml_check_0*.py` currently pass.

---

## 6. Files

```
aml/improve/live.py        the live A/B - subset, pairing, sign test, gate
aml/improve/optimise.py    sign test, consensus, Evaluation, the tri-state gate
aml/improve/mining.py      clusters on observable features, materiality floor
aml/improve/tokenomics.py  spend clusters, live token measurement
aml/improve/bands.py       sigma from the measurement's own standard error
aml/improve/contract.py    the value contract
scripts/ui/improves.js     the four panels
```

| Endpoint | Returns |
|---|---|
| `GET /api/improve/recorded` | clusters, proposals, evaluations, decisions, noise floor, bands, realisation |
| `POST /api/improve/ab` | start a live A/B; body sets `proposal_id`, `alert_ids`, `repeats` |
| `GET /api/improve/stream` | the A/B as it happens |
| `POST /api/improve/tokens` | measure the system prefix with two real calls |
