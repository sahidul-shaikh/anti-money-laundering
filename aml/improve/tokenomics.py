"""The same loop, applied to spend.

Two of these levers are real savings. One is the trap: it is dramatically
cheaper and the gate refuses it, because the quality bar does not move to
make a number look good.
"""

from __future__ import annotations

from dataclasses import dataclass

from aml.corpus.model import Alert
from aml.improve.optimise import COST, Proposal
from aml.llm.bedrock import BedrockProvider
from aml.llm.fleet import CACHE_READ_RATE, ModelSpec, load_fleet
from aml.run.config import case_count


@dataclass(frozen=True)
class SpendCluster:
    """Where the money goes, and what could be done about it."""

    cluster_id: str
    name: str
    share_of_spend: float
    basis: str
    lever: str
    estimated_saving: str
    verdict: str

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "share_of_spend": round(self.share_of_spend, 4),
            "basis": self.basis,
            "lever": self.lever,
            "estimated_saving": self.estimated_saving,
            "verdict": self.verdict,
        }


def measure_system_tokens(spec: ModelSpec, system: str) -> int:
    """Count the fixed prefix by asking the provider, not by estimating."""
    provider = BedrockProvider()
    with_system = provider.complete(spec, system, "x", max_tokens=1)
    without = provider.complete(spec, "", "x", max_tokens=1)
    return max(with_system.tokens_in - without.tokens_in, 0)


def mine_spend(
    ledger_summary: dict,
    cheap_summary: dict,
    corpus: list[Alert],
    system_tokens: int,
) -> list[SpendCluster]:
    """Cost clusters, priced from the two baseline runs that actually happened."""
    calls = max(ledger_summary["calls"], 1)
    tokens_in = max(ledger_summary["tokens_in"], 1)
    prefix_tokens = system_tokens * calls
    prefix_share = min(prefix_tokens / tokens_in, 1.0)

    alerts, cases = len(corpus), case_count(corpus)
    reviews_saved = alerts - cases

    accuracy_drop = ledger_summary["accuracy"] - cheap_summary["accuracy"]
    cost_drop = 1 - (cheap_summary["cost_usd"] / max(ledger_summary["cost_usd"], 1e-9))

    rejected = next(m for m in load_fleet() if not m.serving)
    rejected_ratio = (rejected.price_in + rejected.price_out) / 2.0

    return [
        SpendCluster(
            "TOK-01",
            "Fixed instruction prefix resent on every alert",
            prefix_share,
            f"{system_tokens} system tokens on each of {calls} calls, "
            f"{prefix_tokens:,} of {tokens_in:,} input tokens",
            "cache the prefix; a cached read bills at "
            f"{CACHE_READ_RATE:.0%} of the input rate",
            f"up to {prefix_share * (1 - CACHE_READ_RATE):.0%} of input spend",
            "available on models that support prompt caching; neither serving "
            "model in this fleet does, so it is costed and left open",
        ),
        SpendCluster(
            "TOK-02",
            "One human review per alert rather than per party",
            0.0,
            f"{alerts} alerts resolve to {cases} parties, so {reviews_saved} "
            f"reviews are duplicates of one already being done",
            "consolidate alerts by party before they reach the queue",
            f"{reviews_saved} reviews at GBP 17.00 = GBP {reviews_saved * 17.0:.0f} "
            f"across the corpus",
            "the dominant cost is human time, not tokens",
        ),
        SpendCluster(
            "TOK-03",
            "Every alert goes to the premium tier",
            1.0,
            f"premium ${ledger_summary['cost_usd']:.4f} against cheap "
            f"${cheap_summary['cost_usd']:.4f} on the same 70 alerts",
            "route everything to the cheap tier",
            f"{cost_drop:.0%} of model spend",
            f"REFUSE: accuracy falls {accuracy_drop:.1%} "
            f"({ledger_summary['accuracy']:.1%} to {cheap_summary['accuracy']:.1%})",
        ),
        SpendCluster(
            "TOK-04",
            f"A cheaper model exists outside the serving fleet ({rejected.model})",
            0.0,
            f"${rejected_ratio:.2f} per MTok blended against premium, with "
            f"{rejected.quality:.0%} measured recall ({rejected.quality_basis})",
            "demote the fleet to the cheapest model available",
            "roughly an order of magnitude on model spend",
            f"REFUSE: {rejected.quality:.0%} recall means it misses most "
            f"suspicious activity; it is in the fleet only so it can be priced",
        ),
    ]


def cost_proposals(clusters: list[SpendCluster]) -> list[Proposal]:
    """Only the levers this codebase can actually pull become proposals."""
    proposals = []
    for cluster in clusters:
        if cluster.cluster_id != "TOK-02":
            continue
        proposals.append(
            Proposal(
                proposal_id="CST-01",
                kind=COST,
                change="consolidate_by_party",
                rationale=cluster.basis,
                evidence=cluster.estimated_saving,
                expected="lower cost per outcome with no loss of accuracy",
            )
        )
    return proposals
