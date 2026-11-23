"""Five-layer observability, computed from the ledger.

Uptime and error rate answer none of the questions a regulator asks about an
AI control. These five layers do: is it up, what did it cost, is it grounded,
is it right, and is it worth running.
"""

from __future__ import annotations

import collections
import statistics

from aml.core.ledger import MANUAL_REVIEW_GBP, Ledger
from aml.run.engine import PROVIDER_ERROR, UNPARSEABLE, Disposition

# What the alert costs today: one analyst, one review, every time.
BASELINE_GBP = MANUAL_REVIEW_GBP


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def layers(ledger: Ledger, dispositions: list[Disposition]) -> dict:
    ok_calls = [c for c in ledger.calls if c.status == "ok"]
    latencies = [float(c.latency_ms) for c in ok_calls]
    tokens_in, tokens_out = ledger.tokens
    outcomes = ledger.outcomes
    total = len(outcomes) or 1

    escalated = sum(o.disposition == "escalate_to_case" for o in outcomes)
    auto_closed = sum(o.disposition == "close_no_further_action" for o in outcomes)
    unparseable = sum(o.disposition == UNPARSEABLE for o in outcomes)
    provider_errors = sum(o.disposition == PROVIDER_ERROR for o in outcomes)
    cost_per_outcome = ledger.cost_per_outcome_gbp()

    return {
        "SYSTEM": {
            "calls": len(ledger.calls),
            "failed_calls": ledger.failures(),
            "availability": round(len(ok_calls) / max(len(ledger.calls), 1), 4),
            "latency_p50_ms": round(statistics.median(latencies)) if latencies else 0,
            "latency_p95_ms": round(_percentile(latencies, 0.95)),
            "provider_errors": provider_errors,
        },
        "MODEL": {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(ledger.cost_usd, 6),
            "model_mix": ledger.model_mix(),
            "cost_by_tier": ledger.cost_by_tier(),
        },
        "AGENT": {
            "groundedness": round(ledger.groundedness(), 4),
            "citations": sum(o.cited for o in outcomes),
            "invented_citations": ledger.invented_citations(),
            "unparseable": unparseable,
            "mean_confidence": round(
                sum(o.confidence for o in outcomes) / total, 4
            ),
        },
        "TRANSACTION": {
            "accuracy": round(ledger.accuracy(), 4),
            "recall": round(ledger.recall(), 4),
            "specificity": round(ledger.specificity(), 4),
            "disposition_mix": dict(
                collections.Counter(o.disposition for o in outcomes)
            ),
            "by_scenario": _by_scenario(outcomes),
        },
        "VALUE": {
            "baseline_gbp_per_alert": BASELINE_GBP,
            "cost_per_outcome_gbp": round(cost_per_outcome, 4),
            "saving_per_alert_gbp": round(BASELINE_GBP - cost_per_outcome, 4),
            "saving_share": round((BASELINE_GBP - cost_per_outcome) / BASELINE_GBP, 4),
            "auto_resolution_rate": round(auto_closed / total, 4),
            "escalation_rate": round(escalated / total, 4),
        },
    }


def _by_scenario(outcomes) -> dict:
    grouped = collections.defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.scenario].append(outcome)
    return {
        scenario: {
            "n": len(items),
            "accuracy": round(sum(o.correct for o in items) / len(items), 4),
        }
        for scenario, items in sorted(grouped.items())
    }
