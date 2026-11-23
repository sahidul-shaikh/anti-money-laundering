"""Propose a change, measure it on the same corpus, and put it to a gate.

Nothing here decides anything on its own. A proposal carries the evidence
that produced it; an evaluation is a real run; the gate is a rule that can
and does refuse.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aml.corpus.model import Alert
from aml.core.ledger import Ledger
from aml.improve.mining import Cluster
from aml.run.config import AgentConfig
from aml.run.engine import RunConfig, run_corpus

ACCURACY = "accuracy"
COST = "cost"

# How much accuracy a cost saving may buy. One point. The quality bar does
# not move to make a saving look good.
QUALITY_TOLERANCE = 0.01

# A change to a regulated control needs evidence, not a nicer number.
ALPHA = 0.05


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    kind: str
    change: str
    rationale: str
    evidence: str
    expected: str

    def apply_to(self, config: AgentConfig) -> AgentConfig:
        return config.with_change(**{self.change: True})

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind,
            "change": self.change,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "expected": self.expected,
        }


def sign_test(improved: int, regressed: int) -> float:
    """Two-sided exact sign test on the alerts that changed their answer.

    Aggregate percentages are the wrong instrument here: the same
    configuration run twice moves several points on a corpus of seventy. The
    comparison is paired - the same alerts, before and after - so the only
    thing worth counting is which way each disagreement went.
    """
    n = improved + regressed
    if n == 0:
        return 1.0
    extreme = max(improved, regressed)
    tail = sum(math.comb(n, k) for k in range(extreme, n + 1)) / 2**n
    return min(1.0, 2 * tail)


@dataclass
class Evaluation:
    proposal: Proposal
    before: dict
    after: dict
    before_correct: dict[str, bool] = field(default_factory=dict)
    after_correct: dict[str, bool] = field(default_factory=dict)
    cost_usd: float = 0.0

    def delta(self, metric: str) -> float:
        return self.after[metric] - self.before[metric]

    @property
    def flips(self) -> tuple[int, int]:
        """Alerts that went wrong to right, and right to wrong."""
        shared = set(self.before_correct) & set(self.after_correct)
        improved = sum(
            1 for a in shared if not self.before_correct[a] and self.after_correct[a]
        )
        regressed = sum(
            1 for a in shared if self.before_correct[a] and not self.after_correct[a]
        )
        return improved, regressed

    @property
    def p_value(self) -> float:
        return sign_test(*self.flips)

    def to_dict(self) -> dict:
        improved, regressed = self.flips
        return {
            "proposal": self.proposal.to_dict(),
            "before": self.before,
            "after": self.after,
            "deltas": {
                m: round(self.delta(m), 4)
                for m in ("accuracy", "recall", "specificity", "cost_per_outcome_gbp")
            },
            "improved": improved,
            "regressed": regressed,
            "p_value": round(self.p_value, 4),
            "evaluation_cost_usd": round(self.cost_usd, 5),
        }


APPROVED = "approved"
REFUSED = "refused"
INSUFFICIENT = "insufficient_evidence"


@dataclass
class Decision:
    """Three outcomes, because "no" and "we cannot tell yet" are not the same.

    Collapsing them would either block real improvements forever or let a
    coin toss decide whether a change to a regulated control ships.
    """

    proposal_id: str
    outcome: str
    reason: str
    approver: str = ""

    @property
    def approved(self) -> bool:
        return self.outcome == APPROVED

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "outcome": self.outcome,
            "approved": self.approved,
            "reason": self.reason,
            "approver": self.approver,
        }


def propose(clusters: list[Cluster]) -> list[Proposal]:
    """One proposal per distinct change the clusters point at."""
    by_change: dict[str, list[Cluster]] = {}
    for cluster in clusters:
        if cluster.proposal:
            by_change.setdefault(cluster.proposal, []).append(cluster)

    proposals = []
    for index, (change, group) in enumerate(sorted(by_change.items()), start=1):
        failures = sum(c.count for c in group)
        cost = sum(c.cost_gbp for c in group)
        proposals.append(
            Proposal(
                proposal_id=f"ACC-{index:02d}",
                kind=ACCURACY,
                change=change,
                rationale=" ".join(c.root_cause for c in group[:2]),
                evidence=(
                    f"{failures} failures across {len(group)} clusters "
                    f"({', '.join(c.signature for c in group)}) costing GBP {cost:.2f}"
                ),
                expected=f"recover some of the GBP {cost:.2f} without losing recall",
            )
        )
    return proposals


def consensus(
    corpus: list[Alert],
    config: AgentConfig,
    repeats: int = 3,
    workers: int = 8,
    label: str = "run",
) -> tuple[dict[str, bool], dict, float]:
    """Run the same configuration several times and take the per-alert majority.

    One run is not a measurement. Repeating the evaluation and scoring the
    consensus is the cheapest way to tell a real change from the model
    disagreeing with itself, and it costs pence.
    """
    votes: dict[str, list[bool]] = {}
    summaries, spend = [], 0.0
    for attempt in range(repeats):
        ledger = Ledger()
        run_corpus(
            corpus,
            RunConfig(workers=workers, agent=config, label=f"{label}-{attempt + 1}"),
            ledger=ledger,
        )
        for outcome in ledger.outcomes:
            votes.setdefault(outcome.alert_id, []).append(outcome.correct)
        summaries.append(ledger.summary())
        spend += ledger.cost_usd

    agreed = {a: sum(v) * 2 > len(v) for a, v in votes.items()}
    averaged = {
        key: round(sum(s[key] for s in summaries) / len(summaries), 4)
        for key in ("accuracy", "recall", "specificity", "groundedness",
                    "cost_per_outcome_gbp", "cost_usd")
    }
    averaged["repeats"] = repeats
    averaged["unstable_alerts"] = sum(
        1 for v in votes.values() if 0 < sum(v) < len(v)
    )
    return agreed, averaged, spend


def evaluate(
    proposal: Proposal,
    corpus: list[Alert],
    baseline: dict,
    base_config: AgentConfig,
    before_correct: dict[str, bool],
    repeats: int = 3,
    workers: int = 8,
) -> Evaluation:
    """Run the corpus again with the change applied. Same alerts, same model."""
    after_correct, summary, spend = consensus(
        corpus, proposal.apply_to(base_config), repeats, workers, proposal.proposal_id
    )
    return Evaluation(
        proposal=proposal,
        before=baseline,
        after=summary,
        before_correct=before_correct,
        after_correct=after_correct,
        cost_usd=spend,
    )


def review(evaluation: Evaluation, approver: str, alpha: float = ALPHA) -> Decision:
    """The gate.

    Quality is judged on the paired per-alert comparison, because an
    aggregate percentage on seventy alerts moves by more than most of these
    changes are worth. A cost saving still has to clear the quality bar; the
    bar does not move to let it through.
    """
    proposal = evaluation.proposal
    improved, regressed = evaluation.flips
    p = evaluation.p_value
    cost = evaluation.delta("cost_per_outcome_gbp")
    evidence = f"{improved} improved, {regressed} regressed, p={p:.3f}"

    if proposal.kind == ACCURACY:
        if regressed > improved and p < alpha:
            return Decision(proposal.proposal_id, REFUSED,
                            f"significantly worse: {evidence}")
        if p >= alpha:
            return Decision(
                proposal.proposal_id, INSUFFICIENT,
                f"cannot be told apart from noise at this sample size: {evidence}",
            )
        return Decision(proposal.proposal_id, APPROVED,
                        f"{evidence}; cost per outcome GBP {cost:+.2f}", approver)

    # A cost proposal carries the burden of showing quality was kept, which is
    # the opposite of the accuracy case.
    if cost >= 0:
        return Decision(proposal.proposal_id, REFUSED,
                        f"no saving ({cost:+.2f} GBP per outcome)")
    if regressed > improved and p < alpha:
        return Decision(
            proposal.proposal_id, REFUSED,
            f"saves GBP {abs(cost):.2f} per outcome but quality falls "
            f"measurably: {evidence}",
        )
    if regressed > improved:
        return Decision(
            proposal.proposal_id, INSUFFICIENT,
            f"saves GBP {abs(cost):.2f} per outcome, but quality moved the wrong "
            f"way inside the noise: {evidence}. Needs a larger evaluation corpus "
            f"before it can ship",
        )
    return Decision(
        proposal.proposal_id, APPROVED,
        f"saves GBP {abs(cost):.2f} per outcome, quality intact: {evidence}",
        approver,
    )
