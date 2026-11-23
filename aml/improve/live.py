"""Measure one proposed change, live, on the alerts that provoked it.

The full evaluation in ``scripts/run_improve.py`` runs seventy alerts three
times for each configuration and takes about fifteen minutes. That is the right
way to decide whether a change ships, and it is too slow to watch.

This runs the same machinery - the same ``run_corpus``, the same per-alert
pairing, the same sign test, the same gate - over the subset of alerts a
failure cluster actually identified. It shows the mechanism honestly and it
reaches a verdict in under a minute.

What it cannot do is reach significance. A dozen alerts cannot produce the six
one-way flips a two-sided sign test needs at p<0.05, and the console says so
rather than implying otherwise. The statistics live in the recorded run; the
mechanism is what you watch here.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from aml.corpus.model import Alert
from aml.improve.optimise import Evaluation, Proposal, consensus, review
from aml.run.config import AgentConfig


@dataclass(frozen=True)
class ImproveEvent:
    kind: str
    text: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "data": self.data}


def _calls(n_alerts: int, repeats: int) -> int:
    return n_alerts * repeats * 2


def ab_live(
    corpus: list[Alert],
    alert_ids: list[str],
    proposal: Proposal,
    base: AgentConfig | None = None,
    approver: str = "Head of Financial Crime Technology",
    repeats: int = 1,
    workers: int = 6,
) -> Iterator[ImproveEvent]:
    """Run a subset before and after a change, then put it to the gate."""
    base = base or AgentConfig()
    wanted = set(alert_ids)
    subset = [a for a in corpus if a.alert_id in wanted]
    if not subset:
        yield ImproveEvent("error", "none of those alerts are in the corpus")
        return

    changed = proposal.apply_to(base)
    yield ImproveEvent(
        "plan",
        f"{len(subset)} alerts, {repeats} run(s) each, before and after - "
        f"{_calls(len(subset), repeats)} calls",
        {
            "alerts": [
                {"alert_id": a.alert_id, "party": a.party.name,
                 "scenario": a.scenario, "label": a.label,
                 "provenance": a.provenance}
                for a in subset
            ],
            "proposal": proposal.to_dict(),
            "base_changes": base.changes,
            "changed_changes": changed.changes,
            "repeats": repeats,
            "calls": _calls(len(subset), repeats),
            "significance_possible": len(subset) >= 12,
        },
    )

    yield ImproveEvent(
        "arming", "running the subset as it is configured today", {"arm": "before"})
    before_correct, before, spend_before = consensus(
        subset, base, repeats, workers, "live-before")
    yield ImproveEvent(
        "measured",
        f"before: {sum(before_correct.values())} of {len(before_correct)} correct",
        {"arm": "before", "summary": before,
         "correct": before_correct, "cost_usd": round(spend_before, 6)},
    )

    yield ImproveEvent(
        "arming",
        f"running the same alerts with {proposal.change} applied",
        {"arm": "after", "change": proposal.change},
    )
    after_correct, after, spend_after = consensus(
        subset, changed, repeats, workers, "live-after")
    yield ImproveEvent(
        "measured",
        f"after: {sum(after_correct.values())} of {len(after_correct)} correct",
        {"arm": "after", "summary": after,
         "correct": after_correct, "cost_usd": round(spend_after, 6)},
    )

    evaluation = Evaluation(
        proposal=proposal, before=before, after=after,
        before_correct=before_correct, after_correct=after_correct,
        cost_usd=spend_before + spend_after,
    )
    improved, regressed = evaluation.flips

    shared = sorted(set(before_correct) & set(after_correct))
    rows = [
        {
            "alert_id": a,
            "before": before_correct[a],
            "after": after_correct[a],
            "flip": ("improved" if not before_correct[a] and after_correct[a]
                     else "regressed" if before_correct[a] and not after_correct[a]
                     else "unchanged"),
        }
        for a in shared
    ]
    yield ImproveEvent(
        "flips",
        f"{improved} improved, {regressed} regressed, "
        f"{len(rows) - improved - regressed} unchanged",
        {"rows": rows, "improved": improved, "regressed": regressed,
         "p_value": round(evaluation.p_value, 4)},
    )

    decision = review(evaluation, approver)
    yield ImproveEvent(
        "gate",
        f"{decision.outcome}: {decision.reason}",
        {"decision": decision.to_dict(), "evaluation": evaluation.to_dict()},
    )

    yield ImproveEvent(
        "final",
        "the gate has ruled on the subset",
        {
            "decision": decision.to_dict(),
            "improved": improved,
            "regressed": regressed,
            "p_value": round(evaluation.p_value, 4),
            "accuracy_delta": round(evaluation.delta("accuracy"), 4),
            "cost_delta_gbp": round(evaluation.delta("cost_per_outcome_gbp"), 2),
            "cost_usd": round(evaluation.cost_usd, 6),
            "subset": len(subset),
            "significance_possible": len(subset) >= 12,
        },
    )
