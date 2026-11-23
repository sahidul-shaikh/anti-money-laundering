# The use case - AML alert triage

Read this first. It is the ten minutes before the console is opened: what the
problem is, what we built against it, and what we are claiming.

Companions: **[ARCHITECTURE.md](ARCHITECTURE.md)** for how the product is put
together, and the four pillar runbooks for how to operate the demonstration.

---

## 1. The problem

A bank runs transaction monitoring. Rules written against a vendor model -
here, Actimize AML SAM - watch every account and raise an alert whenever a
pattern crosses a threshold. Structuring. Excessive cash equivalents. A burst
of transfers into one beneficiary. The same identity on three addresses.

Each alert goes to a human investigator, who opens the party record, reads the
transactions, forms a view, and writes it down. The output is one of three
things: close it, escalate it to a case, or ask for more information.

Four things are true about that work at once.

**Most of it is a false positive.** The rules are tuned to miss nothing, which
means they fire on salaries, trading rhythms, settlement cheques and house
deposits. The investigator's day is mostly spent writing down why ordinary
money is ordinary.

**It is expensive.** The contract this product was funded against prices manual
handling at **GBP 17.00 per alert**, all in. At industry alert volumes that is
a standing cost measured in millions, and it grows with the book.

**It is slow, and the clock is regulatory.** A suspicious activity report has a
filing deadline. A backlog is not an efficiency problem, it is a compliance
exposure.

**It is inconsistent.** Two investigators, the same alert, different days -
different write-ups. That inconsistency is itself a model risk finding.

And the obvious reply - "tune the rules" - is the wrong lever. Raising a
threshold reduces alerts by missing things. The regulator is not interested in
a cheaper control that catches less.

### What makes this hard for an AI

Three things, and they are the reason this use case was chosen rather than
something safer.

- **The cost of being wrong is asymmetric and both directions hurt.** A missed
  escalation is a laundering event that went unreported. A wrong escalation
  costs an investigator's day. One of those is a regulatory failure and the
  other is waste, so they cannot be traded one for one.
- **The agent reads attacker-controlled text.** Payment reference fields are
  written by whoever sent the payment. In a monitoring system that text travels
  unmodified into the prompt of whatever reads the alert. It is the one
  genuinely hostile surface in the pipeline.
- **Telling a party they are under investigation is a criminal offence**, not a
  policy breach - 31 U.S.C. 5318(g)(2). An agent that generates customer-facing
  text in this domain is one bad completion away from tipping off.

---

## 2. What the data actually is

Not a fixture. An extract of real transaction-monitoring output
(`AntiMoneyLaundering/Alert_Final_table.xlsx`):

| | |
|---|---|
| Alerts | 35, every one of which escalated and filed |
| Transaction rows | 828 |
| Parties | 25, with dates of birth, occupations and declared income |
| Reports filed | 25 SAR / CTR |
| Scenarios | 6 SAS codes, mapped to 4 Actimize detection models |

Every alert in the extract escalated. That is a problem for measurement: an
agent that escalates everything would score full marks. So the corpus carries
**35 synthetic alerts a competent investigator would close** - a military
salary, a hardware shop paying suppliers, a settlement cheque banked and left
alone - built from archetypes, labelled `synthetic` everywhere they appear, and
never mixed into a claim about real data.

**The loaded corpus is 70 alerts: 35 escalate, 35 close, 1,073 transactions.**
Balanced by construction, so accuracy means something.

The detection thresholds come from the **Actimize AML SAM 8.5.0 Solution
Guide**, 677 pages, product confidential. 28 rule specifications across four
models were extracted into a catalogue the agent retrieves from by scenario
code - so the agent carries the rule the alert actually fired, with the page it
came from, rather than prose someone transcribed by hand.

---

## 3. What we built

**An AML alert investigator.** It reads one alert the way an investigator reads
it - the party, the account, the rule that fired, the transactions - and
returns a disposition with its reasoning and its citations:

- `close_no_action`
- `escalate_to_case`
- `insufficient_information`

Every transaction reference it cites is checked against the alert
deterministically. A citation that is not in the alert is not a judgement call,
it is a fact, and the run is marked ungrounded.

### Three boundaries that are not negotiable

These are enforced in code, not asserted in a slide.

1. **The agent recommends. It never files.** There is no tool that can submit a
   SAR, close an alert in the case management system, or amend a party record.
   The destructive scopes are not merely ungranted - they are *ungrantable*. A
   compromised prompt, a persuaded operator and a bug all hit the same wall.
2. **A human reviews every escalation. Nobody reviews a close.** That asymmetry
   is deliberate and it is where the saving comes from - and it is also the
   risk, which is why recall has a floor.
3. **Nothing the agent writes goes to a customer.** Customer-facing text is
   guarded against disclosure of suspicion, because that disclosure is a
   criminal offence.

### The value contract

Agreed before the build, measured after every run, and the thing any proposed
change is scored against:

| | |
|---|---|
| Baseline | **GBP 17.00** per alert, manual |
| Target | **GBP 12.00** per alert |
| Recall floor | **0.90** - escalations must not be missed |
| Accuracy floor | **0.85** |
| Telemetry | SYSTEM, MODEL, AGENT, TRANSACTION, VALUE |
| Approver | Head of Financial Crime Technology |

Without a contract there is nothing to improve towards and no way to say
whether a change helped. Every number the console prints is measured against
this one.

---

## 4. How the four pillars land on this use case

The demonstration is not four slides about AI. It is one product, built, run,
attacked and improved in front of the room.

**AI builds AI.** The product went through twelve governed stages - value
contract, specification, threat model, architecture, implementation,
evaluation, security review, model risk, deployment - each one generated, each
one gated, each one inheriting reusable skills from a library. The
implementation stage writes a structuring detector and its tests against a
contract it cannot fully see, an independent acceptance suite judges it, and
the failure is fed back as the next instruction until it passes or the gate
refuses.

**AI runs AI.** Every alert is routed to the cheapest serving model that clears
a measured quality floor, with provider fallback, a spend cap, and a ledger
entry for every call. When a cheap model answers but cannot show its working,
policy escalates it to the premium tier rather than accepting an ungrounded
answer. Five layers of observability are computed from the ledger - is it up,
what did it cost, is it grounded, is it right, is it worth running.

**AI secures AI.** Attack payloads are carried where a real attacker would
carry them: in payment reference text. The same payload is fired twice at the
same alert and the same model - once with the reference text inline, once
inside an untrusted-data envelope - so the only variable is the framing.
Whether the attack worked is decided deterministically, never by asking another
model.

**AI improves AI.** Failures are clustered on features visible in the alert,
never on the answer key. A cluster produces a proposal, the proposal is
evaluated on the same corpus against the same baseline with a paired sign test,
and a gate approves or refuses. The gate refuses changes that save money by
lowering quality, and it has.

---

## 5. What we are not claiming

Said up front, because a sharp audience gets there anyway.

- **No accuracy headline.** The rule catalogue changed after the last full
  baseline and there has been no 70-alert re-run since. The per-model quality
  figures in the fleet (3/8, 6/8 and 8/8 escalation recall, measured
  2026-11-09) are the honest numbers, and they are a small sample.
- **The generated detector is not wired in.** The factory writes it and 20
  tests prove it; nothing consumes it yet. Using it as a deterministic
  pre-filter would be better design than leaving a testable arithmetic rule to
  a language model.
- **The running agent was written by hand.** The twelve stages produce the
  governance artifacts and one module, not the whole product.
- **Prompt caching is unavailable, not unused.** Both serving models refuse a
  cache point; the only model in the fleet that caches is the one the quality
  gate rejected. That is a procurement decision, and the saving is pennies
  against GBP 17.00 of human review anyway.
- **The corpus is 70 alerts.** Enough to measure a change with a sign test. Not
  enough to certify a control.
