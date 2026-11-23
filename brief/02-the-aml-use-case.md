# 02 — The AML use case

## The problem

A bank's transaction monitoring raises an alert whenever a pattern crosses a
threshold. An analyst then opens the party record, the KYC file, the
transactions and any prior alerts, forms a view and writes it down.

Four things are true at once:

- **Most of it is a false positive.** The rules are tuned to miss nothing, so
  they fire on salaries, trading rhythms, settlement cheques and house
  deposits. The analyst's day is spent writing down why ordinary money is
  ordinary.
- **It is expensive.** The contract prices manual handling at **GBP 17.00 per
  alert**, all in.
- **It is slow, and the clock is regulatory.** A suspicious activity report has
  a filing deadline. A backlog is a compliance exposure, not an efficiency
  problem.
- **It is inconsistent.** Two investigators, the same alert, different days,
  different write-ups.

The obvious reply — tune the rules down — is the wrong lever. Raising a
threshold reduces alerts by missing things, and no supervisor accepts a
cheaper control that catches less.

## Why this use case is hard for an AI

Stated plainly, because it shapes everything in the architecture.

- **The cost of error is asymmetric and both directions hurt.** A missed
  escalation is unreported laundering. A wrong escalation costs an
  investigator's day. They cannot be traded one for one.
- **The agent reads attacker-controlled text.** Payment reference fields are
  written by the remitter and travel unmodified into the prompt. It is the one
  genuinely hostile surface in the pipeline.
- **Telling a party they are under investigation is a criminal offence** —
  31 U.S.C. 5318(g)(2) — not a policy breach. An agent generating
  customer-facing text here is one bad completion from tipping off.

---

## The data — real, and the honesty problem it creates

`AntiMoneyLaundering/Alert_Final_table.xlsx`:

| | |
|---|---|
| Alerts | 35, every one of which escalated and filed |
| Transaction rows | 828 |
| Parties | 25, with dates of birth, occupations and declared income |
| Reports filed | 25 SARX, 9 CTR, 1 CTRX |
| Cases | 25 — **six cases carry 2 to 4 alerts each** |
| Scenarios | 6 SAS codes across 4 Actimize detection models |

**Every alert in the extract escalated.** An agent that escalates everything
would score full marks. So the corpus carries **35 synthetic alerts a competent
investigator would close** — a military salary, a hardware shop paying
suppliers, a settlement cheque banked and left alone — labelled `synthetic`
everywhere they appear.

**Loaded corpus: 70 alerts, 35 escalate / 35 close, 1,073 transactions, 60
parties, 6 scenarios.** Balanced by construction, so accuracy means something.

### The label trap — important

A naive labelling of "filed = should escalate" is wrong twice over:

- **A CTR is a threshold obligation.** Cash above a regulatory limit must be
  reported whether or not anything is suspicious. Ten of the 35 are therefore
  not evidence of suspicion at all.
- **A closed alert is weak evidence of innocence** too.

The target design separates `outcome` (what the bank did), `adjudication`
(what a reviewer concluded) and `label` (what is used for scoring, with a basis
and a confidence). **The current demonstration has not implemented that
separation** — see `brief/04`. Do not quote an accuracy figure from this system
without reading `design/10-data-model.md` §6 first.

### Detection rules

28 rule specifications across 4 detection models (AML-STR structuring, AML-ECT
excessive cash equivalents, AML-EBB burst in beneficiary activity, AML-MLT
customer identity discovery) were extracted from a 677-page Actimize Solution
Guide into `library/aml/rules.json`, **each carrying the page it came from**.
The agent retrieves the rule the alert actually fired, with its citation,
rather than carrying prose somebody transcribed.

### Scenarios in scope

| Scenario | Description | Model |
|---|---|---|
| SAS10014 | Structured Withdrawals | AML-STR |
| SAS10056 | Structured Premiums | AML-STR |
| SAS10016 | Structured Deposits Across Locations | AML-STR |
| SAS10050 | Payments Using High-Risk Instruments | AML-ECT |
| SAS10602 | Multiple External Remitters, One Internal Beneficiary | AML-EBB |
| SAS10012 | Recurring Phone Number | AML-MLT |

> SAS10602 and SAS10012 need counterparty and relationship data the extract
> does not carry. The agent cannot really reason about them today.

---

## What was built

An agent that reads one alert and returns a disposition with its reasoning and
citations:

- `close_no_action`
- `escalate_to_case`
- `insufficient_information`

Every cited transaction reference is checked against the alert
deterministically. A citation not in the alert is a fact, not a judgement call,
and the run is marked ungrounded.

### Three boundaries, enforced in code

1. **The agent recommends. It never files.** Destructive scopes are
   *unregisterable* — `aml/security/tools.py`.
2. **A human reviews every escalation.** Nobody reviews a close. That asymmetry
   is where the saving comes from and is also the risk, which is why recall has
   a floor.
3. **Nothing the agent writes goes to a customer** — `aml/security/emit.py`.

### The value contract

| | |
|---|---|
| Baseline | **GBP 17.00** per alert |
| Target | **GBP 12.00** per alert |
| Recall floor | **0.90** — binding |
| Accuracy floor | 0.85 |
| Telemetry | SYSTEM, MODEL, AGENT, TRANSACTION, VALUE |
| Approver | Head of Financial Crime Technology |

Recall is the binding constraint. The regulator's question is never how much
was saved; it is what was missed.

---

## The worked example to know

**Alert S90009.** Thomas Brennan, serving soldier, declared income $68,900.
Four credits of **$3,960 on the 26th of each month**, then a **$12,672**
payment two days after the fourth.

The agent escalated, and in its own words the four credits were *"suggesting
potential layering or structuring of funds"* — it found the salary and offered
it as evidence against the man.

One rule appended to the standing instructions (`EXPLAIN_BEFORE_ESCALATE` in
`aml/run/config.py`) and the same alert closes, naming the salary as the
explanation. That is the Improves pillar in a single case, and it is the
clearest thing in the demonstration.
