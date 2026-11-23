# Product Requirements: AML Alert Investigator

**Raised by:** Head of Financial Crime Technology
**For:** Financial Crime Operations, US Retail Bank
**Status:** Approved for build
**Date:** 2026-11-10

> This is the only human-authored input to the factory. Everything downstream —
> the specification, the threat model, the architecture, the code, the model risk
> documentation — is derived from this document. Change it and the build changes.

---

## 1. The problem

Our transaction monitoring estate fires several thousand alerts a day across
structuring, high-risk instrument and velocity typologies. More than 95% of them
close with no further action.

A Level-1 analyst currently spends 20 to 40 minutes on each alert: assembling the
party profile, pulling the underlying transactions, deciding whether to close or
escalate, and writing a rationale that a regulator may read years later. We are
carrying a backlog, and the cost per alert is £17.00 of analyst time.

## 2. What we want built

An agent that takes **one alert** and produces a **disposition with evidence**, so
that an analyst reviews a recommendation instead of starting from nothing.

It must handle the six scenarios currently in scope:

| Scenario | Description |
|---|---|
| SAS10014 | Structured Withdrawals |
| SAS10056 | Structured Premiums |
| SAS10016 | Structured Deposits Across Locations |
| SAS10050 | Payments Made Using High-Risk Instruments |
| SAS10602 | Multiple External Remitters, One Internal Beneficiary |
| SAS10012 | Recurring Phone Number |

## 3. Who uses it

Level-1 AML analysts, who act on the recommendation, and the model risk
reviewers who must sign the solution off before it goes anywhere near production.

## 4. Commercial targets

| | |
|---|---|
| Baseline today | £17.00 per alert, one analyst review, every time |
| Target | £12.00 per alert |
| Minimum recall | 90% — of alerts that should escalate, we must escalate 90% |
| Minimum accuracy | 85% |

Recall is the binding constraint. The regulator's question is never "how much did
you save", it is "what did you miss".

## 5. Constraints

These are not preferences. A build that violates any of them is not acceptable.

1. **Evidence.** Every claim the agent makes must cite transaction references that
   exist in the alert it was given. A citation that is not in the data is a defect,
   not a stylistic issue.
2. **No autonomous closure.** The agent may never close an alert by itself. A human
   reviews every escalation and every close.
3. **Tipping off.** Disclosing that a party is under a suspicious activity report
   is a criminal offence under 31 U.S.C. 5318(g)(2). This must be impossible by
   construction, not discouraged by instruction.
4. **Untrusted input.** Payment reference and remittance free text is written by
   whoever sent the payment. It must be treated as evidence to be reported, never
   as instruction to be followed.
5. **Thresholds.** Detection follows the Actimize AML-SAM defaults for the AML-STR
   and AML-ECT models. We are not inventing our own thresholds.
6. **Auditability.** Every disposition must be reproducible from what was recorded.

## 6. Detection rule in scope for implementation

The first deliverable is the structuring detector, per Actimize **AML-STR**,
rule `AML-STR-CCE-INN-A-D01-DST`:

> Detect small but structured incremental cash-equivalent deposits. A transaction
> qualifies when its amount falls between the lower and upper bound. The rule
> fires when the number of qualifying transactions reaches the occurrence
> threshold within a rolling window.

**Actimize default values:**

| Parameter | Default |
|---|---|
| Lower bound | 8,000 |
| Upper bound | 9,999.99 |
| Occurrences | 3 |
| Window | 14 days |

Boundaries are inclusive of the lower bound and inclusive of the upper bound.
A transaction of exactly 10,000.00 does not qualify — it is reportable under
AML-ECT instead and is out of scope for this rule.

Only credits are considered for a deposit-structuring rule. Debits are ignored.

## 7. Integration contract

The detector is called by the existing alert pipeline, so the signature is fixed:

```python
def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    ...
```

**Input** — `transactions` is a list of dictionaries. Each has at least:

| Key | Type | Notes |
|---|---|---|
| `date` | `str` | `YYYYMMDD` |
| `ref` | `str` | the transaction reference |
| `amount` | `float` | |
| `direction` | `str` | `CREDIT` or `DEBIT` |

**Output** — a dictionary with exactly these keys:

| Key | Type | Meaning |
|---|---|---|
| `detected` | `bool` | whether the rule fired |
| `occurrences` | `int` | how many qualifying transactions were found in the window that triggered detection; `0` when nothing qualified |
| `window_start` | `str\|None` | date of the first qualifying transaction in that window, **`YYYY-MM-DD`** |
| `window_end` | `str\|None` | date of the last qualifying transaction in that window, **`YYYY-MM-DD`** |
| `refs` | `list[str]` | references of the qualifying transactions, in date order |
| `total` | `float` | sum of the qualifying transaction amounts, rounded to 2dp |

Transactions arrive from the monitoring extract as `YYYYMMDD`. The two window
dates in the result are **not** in that format: the case management system this
detector feeds takes ISO-8601, so `window_start` and `window_end` are written
`YYYY-MM-DD`. Everything else about a date passes through untouched.

When the rule does not fire, `detected` is `False`, `refs` is empty, `total` is
`0.0`, and both window fields are `None`. Qualifying transactions that exist but
do not reach the occurrence threshold are still reported in `occurrences`.

A window of `window_days` spans that many calendar days **inclusive of both
endpoints**. With the default of 14: transactions dated `d` and `d + 13` both fall
inside the same window; a transaction dated `d + 14` does not.

## 8. Out of scope

- Alert generation and threshold tuning in the monitoring system
- Changes to the case management system
- Filing to FinCEN — the agent drafts, a human files
- Sanctions and watchlist screening
