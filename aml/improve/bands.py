"""How far off target, and what the agent is allowed to do about it.

The band is arithmetic, not judgement. A deviation is expressed in standard
errors of the measurement itself, so "two sigma" means something specific
about this corpus at this size rather than being a label someone chose.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, replace

BAND_1 = 1
BAND_2 = 2
BAND_3 = 3

ACTIONS = {
    BAND_1: "within noise: the agent may tune autonomously",
    BAND_2: "material: proposals allowed, each one needs human approval",
    BAND_3: "severe: automated change is halted pending human triage",
}


@dataclass(frozen=True)
class Detection:
    metric: str
    observed: float
    target: float
    stderr: float
    sigma: float
    band: int
    action: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "observed": round(self.observed, 4),
            "target": round(self.target, 4),
            "stderr": round(self.stderr, 5),
            "sigma": round(self.sigma, 2),
            "band": self.band,
            "action": self.action,
            "note": self.note,
        }


def band_for(sigma: float) -> int:
    if sigma < 1.0:
        return BAND_1
    if sigma < 3.0:
        return BAND_2
    return BAND_3


def proportion_stderr(p: float, n: int) -> float:
    """Standard error of a proportion. The dispersion is in the measurement."""
    if n <= 0:
        return 0.0
    return math.sqrt(max(p * (1 - p), 1e-9) / n)


def mean_stderr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values) / math.sqrt(len(values))


def detect(metric: str, observed: float, target: float, stderr: float) -> Detection:
    """A shortfall against target, in standard errors."""
    shortfall = max(target - observed, 0.0) if "cost" not in metric else max(observed - target, 0.0)
    sigma = shortfall / stderr if stderr else 0.0
    band = band_for(sigma)
    return Detection(
        metric=metric,
        observed=observed,
        target=target,
        stderr=stderr,
        sigma=sigma,
        band=band,
        action=ACTIONS[band],
    )


def escalate(detection: Detection, reason: str, approver: str) -> Detection:
    """A human opens band 3 deliberately, and signs for it.

    Band 3 halts automated change. Re-entry is a human decision, recorded
    with a name against it.
    """
    return replace(
        detection,
        band=BAND_3,
        action=ACTIONS[BAND_3],
        note=f"escalated to band 3 by {approver}: {reason}",
    )


def assess(summary: dict, contract, outcomes: list) -> list[Detection]:
    """Every contract target, banded."""
    n = len(outcomes) or 1
    positives = [o for o in outcomes if o.label == "escalate_to_case"]
    costs = [o.handling_cost_gbp for o in outcomes]
    return [
        detect(
            "accuracy",
            summary["accuracy"],
            contract.target_accuracy,
            proportion_stderr(summary["accuracy"], n),
        ),
        detect(
            "recall",
            summary["recall"],
            contract.target_recall,
            proportion_stderr(summary["recall"], len(positives) or 1),
        ),
        detect(
            "cost_per_outcome_gbp",
            summary["cost_per_outcome_gbp"],
            contract.target_gbp,
            mean_stderr(costs),
        ),
    ]
