"""Every model call and every outcome, recorded once so nothing is asserted twice."""

from __future__ import annotations

import collections
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# Economic overlay. These are stated assumptions, not measurements, and the
# console labels them as such. Everything else in the ledger is computed.
MANUAL_REVIEW_GBP = 17.00      # 30 minutes of L1 analyst time, fully loaded
PLATFORM_OVERHEAD_GBP = 0.20   # storage, queueing and audit per disposition
MISSED_SAR_GBP = 85.00         # QA rework when a wrongly closed alert is sampled
USD_TO_GBP = 0.79


@dataclass(frozen=True)
class CallRecord:
    """One request to one model."""

    ts: str
    run_id: str
    alert_id: str
    tier: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    cost_usd: float
    latency_ms: int
    status: str
    attempt: int
    provenance: str


@dataclass(frozen=True)
class OutcomeRecord:
    """What the agent decided about one alert, and whether it was right."""

    run_id: str
    alert_id: str
    provenance: str
    scenario: str
    label: str
    disposition: str
    correct: bool
    groundedness: float
    cited: int
    invented: int
    confidence: float
    tier: str
    cost_usd: float
    handling_cost_gbp: float


@dataclass
class Ledger:
    calls: list[CallRecord] = field(default_factory=list)
    outcomes: list[OutcomeRecord] = field(default_factory=list)
    # The corpus runs concurrently, so writes are serialised.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_call(self, **kwargs) -> CallRecord:
        record = CallRecord(ts=datetime.now(timezone.utc).isoformat(), **kwargs)
        with self._lock:
            self.calls.append(record)
        return record

    def record_outcome(self, **kwargs) -> OutcomeRecord:
        record = OutcomeRecord(**kwargs)
        with self._lock:
            self.outcomes.append(record)
        return record

    # -- aggregations -----------------------------------------------------

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def tokens(self) -> tuple[int, int]:
        return (
            sum(c.tokens_in for c in self.calls),
            sum(c.tokens_out for c in self.calls),
        )

    def model_mix(self) -> dict[str, int]:
        return dict(collections.Counter(c.tier for c in self.calls if c.status == "ok"))

    def cost_by_tier(self) -> dict[str, float]:
        totals: dict[str, float] = collections.defaultdict(float)
        for call in self.calls:
            totals[call.tier] += call.cost_usd
        return {tier: round(value, 6) for tier, value in totals.items()}

    def failures(self) -> int:
        return sum(1 for c in self.calls if c.status != "ok")

    def accuracy(self) -> float:
        return _ratio(sum(o.correct for o in self.outcomes), len(self.outcomes))

    def recall(self) -> float:
        """Share of genuinely suspicious alerts the agent escalated."""
        positives = [o for o in self.outcomes if o.label == "escalate_to_case"]
        return _ratio(sum(o.correct for o in positives), len(positives))

    def specificity(self) -> float:
        """Share of closable alerts the agent closed."""
        negatives = [o for o in self.outcomes if o.label == "close_no_further_action"]
        return _ratio(sum(o.correct for o in negatives), len(negatives))

    def groundedness(self) -> float:
        return _ratio(sum(o.groundedness for o in self.outcomes), len(self.outcomes))

    def invented_citations(self) -> int:
        return sum(o.invented for o in self.outcomes)

    def cost_per_outcome_gbp(self) -> float:
        return _ratio(sum(o.handling_cost_gbp for o in self.outcomes), len(self.outcomes))

    def summary(self) -> dict:
        tokens_in, tokens_out = self.tokens
        return {
            "calls": len(self.calls),
            "failed_calls": self.failures(),
            "outcomes": len(self.outcomes),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(self.cost_usd, 6),
            "model_mix": self.model_mix(),
            "cost_by_tier": self.cost_by_tier(),
            "accuracy": round(self.accuracy(), 4),
            "recall": round(self.recall(), 4),
            "specificity": round(self.specificity(), 4),
            "groundedness": round(self.groundedness(), 4),
            "invented_citations": self.invented_citations(),
            "cost_per_outcome_gbp": round(self.cost_per_outcome_gbp(), 4),
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "calls": [asdict(c) for c in self.calls],
            "outcomes": [asdict(o) for o in self.outcomes],
        }


def handling_cost_gbp(
    disposition: str, correct: bool, cost_usd: float, review_share: float = 1.0
) -> float:
    """What one disposition costs the bank, model spend included.

    An escalation always buys a human review. A correct close buys only
    platform overhead. A wrong close buys the review anyway, late, plus the
    rework that follows when quality assurance samples it.
    """
    model_cost = cost_usd * USD_TO_GBP
    # Anything that is not a close falls to the human queue, which is simply
    # what happens today. Only a wrong close carries the missed-SAR penalty.
    review = MANUAL_REVIEW_GBP * review_share
    if disposition != "close_no_further_action":
        return round(model_cost + review, 4)
    if correct:
        return round(model_cost + PLATFORM_OVERHEAD_GBP, 4)
    return round(model_cost + review + MISSED_SAR_GBP, 4)


def _ratio(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
