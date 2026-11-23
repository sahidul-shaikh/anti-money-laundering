"""The value contract: what this agent was funded to achieve.

Agreed before the build, measured after every run. Without one there is
nothing to improve towards and no way to say whether a change helped.
"""

from __future__ import annotations

from dataclasses import dataclass

from aml.core.ledger import MANUAL_REVIEW_GBP


class NoValueContract(RuntimeError):
    """A build was attempted with no agreed baseline, target or telemetry."""


@dataclass(frozen=True)
class ValueContract:
    name: str
    baseline_gbp: float
    target_gbp: float
    target_recall: float
    target_accuracy: float
    telemetry: tuple[str, ...]
    approver: str

    def realisation(self, observed: dict) -> dict:
        """How far each target has been met, on the numbers from the run."""
        closed = self.baseline_gbp - observed["cost_per_outcome_gbp"]
        needed = self.baseline_gbp - self.target_gbp
        return {
            "cost_per_outcome_gbp": observed["cost_per_outcome_gbp"],
            "cost_target_gbp": self.target_gbp,
            "cost_target_met": observed["cost_per_outcome_gbp"] <= self.target_gbp,
            "cost_gap_closed": round(closed / needed, 4) if needed else 0.0,
            "recall": observed["recall"],
            "recall_target": self.target_recall,
            "recall_target_met": observed["recall"] >= self.target_recall,
            "accuracy": observed["accuracy"],
            "accuracy_target": self.target_accuracy,
            "accuracy_target_met": observed["accuracy"] >= self.target_accuracy,
            "all_targets_met": (
                observed["cost_per_outcome_gbp"] <= self.target_gbp
                and observed["recall"] >= self.target_recall
                and observed["accuracy"] >= self.target_accuracy
            ),
        }


# Recall is set highest because the regulator's question is never "how much
# did you save"; it is "what did you miss".
INVESTIGATOR_CONTRACT = ValueContract(
    name="AML Alert Investigator",
    baseline_gbp=MANUAL_REVIEW_GBP,
    target_gbp=12.00,
    target_recall=0.90,
    target_accuracy=0.85,
    telemetry=("SYSTEM", "MODEL", "AGENT", "TRANSACTION", "VALUE"),
    approver="Head of Financial Crime Technology",
)


def require_contract(contract: ValueContract | None) -> ValueContract:
    """No contract, no build."""
    if contract is None:
        raise NoValueContract(
            "no agreed baseline, target or telemetry: the build cannot start"
        )
    if not contract.telemetry:
        raise NoValueContract(
            f"{contract.name}: no telemetry agreed, so realisation is unmeasurable"
        )
    return contract
