# 01 — What we are building

## The argument

Organisations have learned to make AI write code quickly. The processes around
the code have not moved at the same pace, so the gain is absorbed by the
stages on either side of the build: planning, review, approval, deployment.

The claim this system exists to prove is narrower and more testable than
"AI makes us faster":

> An AI estate can be **built, run, secured and improved by AI**, under
> governance a regulator would accept, and every claim about it can be
> measured rather than asserted.

Four pillars, demonstrated against **one real product** rather than four
slideware examples. If the pillars do not hold for a financial-crime control
with named individuals and a criminal-offence disclosure risk, they do not
hold.

---

## The four pillars and their 18 disciplines

| Pillar | Claim | Disciplines |
|---|---|---|
| **AI builds AI** | From individual craftsmanship into a repeatable engineering factory | Specs · Context · Skills · Loops · Graphs · Evaluation · Delivery |
| **AI runs AI** | A self-operating estate that adds capacity without adding operations cost | Routing · Reliability · Observability · FinOps |
| **AI secures AI** | Security engineered in at build time, defended live, hardened by what production teaches | Threat modelling · Runtime defense · Swarm pen-testing |
| **AI improves AI** | Every production cycle leaves the estate measurably better than the last | Harness · Tokenomics · Failure mining · Value engineering |

Each discipline is **one panel in the console**, and each panel does the real
thing. The console routes are:

```
/builds/specs  /builds/context  /builds/skills
/builds/loops  /builds/graphs   /builds/evaluation
/builds/delivery
/runs/routing  /runs/reliability  /runs/observability  /runs/finops
/secures/threat-modelling  /secures/runtime-defense  /secures/swarm
/improves/harness  /improves/tokenomics  /improves/failure-mining  /improves/value-engineering
```

---

## What each pillar actually does here

### AI builds AI

A **twelve-stage factory** generates the product's governance artefacts and one
code module. Each stage is a headless Claude Code call that inherits reusable
skills from a library and is gated before the next stage starts.

The stage worth understanding is **Loops**. The implementation stage is handed
the integration contract with part of it deliberately withheld — the output
convention the downstream system requires is in the acceptance suite, not in
the brief. No model can infer it, so **attempt 1 fails every time** (measured
8 times out of 8). The acceptance suite names what is wrong, the feedback
carries back both the pass count and the code the attempt wrote, and attempt 2
passes. The loop, not the model, is what closes the gap.

> Give the same stage the full requirements and it passes 20/20 on the first
> attempt, three times out of three. The failure is caused by the missing
> information, not by model weakness. That distinction is the whole point.

### AI runs AI

Every alert is routed to the **cheapest serving model that clears a measured
quality floor**, with provider fallback, a spend cap, and a ledger entry for
every attempt including failures. When a cheap model answers but cannot cite
evidence that exists in the alert, policy escalates it to a stronger model
rather than accepting an ungrounded answer.

Five layers of observability are computed from the ledger — **SYSTEM** (is it
up), **MODEL** (what did it cost), **AGENT** (is it grounded), **TRANSACTION**
(is it right), **VALUE** (is it worth running). Uptime answers none of the
questions a regulator asks; these five do.

### AI secures AI

Attack payloads are carried where a real attacker would carry them: in
**payment reference free text**, which is written by whoever sent the payment
and reaches the prompt unmodified. The same payload is fired **twice at the
same alert and the same model** — once inline, once inside an untrusted-data
envelope — so the only variable is the framing. Whether the attack worked is
decided deterministically, never by asking another model.

Behind that sits the strongest control in the system: destructive capabilities
(`alert.close`, `sar.file`, `party.write`, `payment.release`, …) are
**unregisterable**, not merely ungranted. Attempting to register one raises at
start-up and the service does not come up.

### AI improves AI

Failures are clustered on features visible in the alert, **never on the
label**. A cluster produces a proposal, the proposal is evaluated on the same
corpus against the same baseline with a paired sign test, and a gate approves
or refuses. The gate refuses changes that buy cost by losing recall, and it
has done so.

Deviations are banded in **standard errors of the measurement itself**, so
"two sigma" means something specific about this corpus at this size rather
than being a label someone chose.

---

## The discipline that holds it together

**Nothing is asserted twice.** Every model call and every outcome is written
once to a single ledger, and every figure anywhere — cost, groundedness,
accuracy, telemetry, the improvement decision — is computed from it.

Three consequences you should preserve:

1. If a panel shows a number, that number came from the ledger.
2. If something cannot be measured, the panel says so rather than estimating.
3. Where a capability is declared but not executed, it says *declared*, not
   *tested*. Nothing is reported as proven that was not proven.
