"""Group the failures, attribute a cause, and point at a fix.

Clustering is done on features visible in the alert itself, never on the
label or the archetype that produced it. A cluster found by reading the
answer key would not survive contact with production.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field

from aml.corpus.model import Alert

# A cluster smaller than this is not worth a change to a regulated control.
MATERIALITY_FLOOR = 3

MISSED = "missed_escalation"
OVER = "over_escalation"


def features(alert: Alert, siblings: int) -> list[str]:
    """What is observably true about this alert, before anyone scores it."""
    txns = alert.transactions
    credits = [t for t in txns if t.direction == "CREDIT"]
    debits = [t for t in txns if t.direction == "DEBIT"]
    found = []

    if siblings > 0:
        found.append("party_has_other_alerts")

    if len(txns) == 1:
        found.append("single_transaction")

    near = [t for t in txns if 8000 <= t.amount <= 9999.99]
    if len(near) == 1:
        found.append("isolated_near_threshold")

    if credits:
        largest = max(credits, key=lambda t: t.amount)
        moved_on = any(d.amount >= largest.amount * 0.5 for d in debits)
        if largest.amount >= 20_000 and not moved_on:
            found.append("large_receipt_retained")

    equal_debits = collections.Counter(round(d.amount, 2) for d in debits)
    if equal_debits and max(equal_debits.values()) >= 3:
        found.append("regular_equal_debits")

    equal_credits = collections.Counter(round(c.amount, 2) for c in credits)
    if equal_credits and max(equal_credits.values()) >= 3:
        found.append("regular_equal_credits")

    if len(txns) >= 30:
        found.append("high_transaction_count")

    return found or ["unremarkable"]


# Signature -> what is actually going wrong, and the change that addresses it.
ROOT_CAUSES = {
    (OVER, "large_receipt_retained"): (
        "The agent treats a large receipt as suspicion in itself. It does not "
        "check whether the money moved on, which is what distinguishes layering "
        "from a settlement that was simply banked.",
        "explain_before_escalate",
    ),
    (OVER, "regular_equal_credits"): (
        "Regular equal credits consistent with declared income are being read "
        "as a burst in beneficiary activity. The agent is not using the income "
        "on the party record as the explanation it is.",
        "explain_before_escalate",
    ),
    (OVER, "regular_equal_debits"): (
        "Equal recurring payments are read as structuring. AML-STR requires "
        "sub-threshold amounts and a 14-day window; a trading rhythm against "
        "visible receipts meets neither.",
        "explain_before_escalate",
    ),
    (MISSED, "party_has_other_alerts"): (
        "Alerts are triaged one at a time, so a leg that looks thin on its own "
        "is closed while its siblings are escalated. The episode is only "
        "visible when the party's alerts are read together.",
        "consolidate_by_party",
    ),
    (MISSED, "single_transaction"): (
        "A single very large instrument payment is closed for lack of a "
        "pattern. AML-ECT fires on one transaction; recurrence is not required.",
        "explain_before_escalate",
    ),
    (MISSED, "high_transaction_count"): (
        "With enough transactions the agent loses the thread and reports no "
        "pattern. Volume is being mistaken for noise.",
        "consolidate_by_party",
    ),
}


@dataclass
class Cluster:
    kind: str
    feature: str
    count: int
    alert_ids: list[str] = field(default_factory=list)
    root_cause: str = ""
    proposal: str = ""
    cost_gbp: float = 0.0

    @property
    def signature(self) -> str:
        return f"{self.kind}:{self.feature}"

    def to_dict(self) -> dict:
        return {
            "signature": self.signature,
            "kind": self.kind,
            "feature": self.feature,
            "count": self.count,
            "alert_ids": self.alert_ids,
            "root_cause": self.root_cause,
            "proposal": self.proposal,
            "cost_gbp": round(self.cost_gbp, 2),
        }


def mine(outcomes, corpus: list[Alert], floor: int = MATERIALITY_FLOOR) -> list[Cluster]:
    """Cluster the failures, biggest first, and attribute each one."""
    alerts = {a.alert_id: a for a in corpus}
    sibling_count = collections.Counter(a.party.number for a in corpus)

    buckets: dict[tuple[str, str], Cluster] = {}
    for outcome in outcomes:
        if outcome.correct:
            continue
        alert = alerts.get(outcome.alert_id)
        if alert is None:
            continue
        kind = MISSED if outcome.label == "escalate_to_case" else OVER
        siblings = sibling_count[alert.party.number] - 1
        for feature in features(alert, siblings):
            key = (kind, feature)
            cluster = buckets.setdefault(key, Cluster(kind=kind, feature=feature, count=0))
            cluster.count += 1
            cluster.alert_ids.append(outcome.alert_id)
            cluster.cost_gbp += outcome.handling_cost_gbp

    material = []
    for (kind, feature), cluster in buckets.items():
        if cluster.count < floor:
            continue
        cause, proposal = ROOT_CAUSES.get(
            (kind, feature),
            ("No attributed cause yet; needs an analyst.", ""),
        )
        cluster.root_cause = cause
        cluster.proposal = proposal
        material.append(cluster)

    return sorted(material, key=lambda c: (-c.cost_gbp, -c.count))


def summarise(clusters: list[Cluster], total_failures: int) -> dict:
    attributed = sum(c.count for c in clusters if c.proposal)
    return {
        "clusters": len(clusters),
        "failures": total_failures,
        "clustered": sum(c.count for c in clusters),
        "attributed": attributed,
        "proposals": sorted({c.proposal for c in clusters if c.proposal}),
        "cost_in_clusters_gbp": round(sum(c.cost_gbp for c in clusters), 2),
    }
