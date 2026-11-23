"""What the agent is configured to do, and the prompt that follows from it.

Each flag is a change the Improve pillar has to propose, measure and get
approved. The base prompt is never edited - additions are appended, so the
stable prefix stays stable and a cache would keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from aml.corpus.model import Alert
from aml.run.prompts import SYSTEM_PROMPT

EXPLAIN_BEFORE_ESCALATE = """

ADDITIONAL RULE: VALUE IS NOT SUSPICION
Before escalating because an amount is large, look for the explanation in the
transactions you were given:
- Is the source of the funds visible in this same list - salary credits, an
  earlier deposit, revenue receipts? Then the source is on the record.
- Did the money move on, or did it stay? A receipt that is retained, with only
  small routine payments after it, is not layering.
- Are payments regular, equal and matched by visible receipts? That is a
  trading rhythm, not structuring.
If the record explains the activity, close it and name what explained it."""

EVIDENCE_FOR_CLOSE = """

ADDITIONAL RULE: A CLOSE NEEDS EVIDENCE TOO
Closing is a decision, not an absence of one. Cite the transactions that
explain the activity, exactly as you would when escalating. A close with no
cited evidence is not acceptable."""

CONSOLIDATION_NOTE = """

ADDITIONAL RULE: READ RELATED ALERTS TOGETHER
Where the alert lists other alerts on the same party, treat them as one
episode. A leg that looks unremarkable alone may be one part of a single
structuring pattern spread across scenarios."""


@dataclass(frozen=True)
class AgentConfig:
    """The agent's settings. Changing one of these is a change to the product."""

    tier: str = "premium"
    explain_before_escalate: bool = False
    evidence_for_close: bool = False
    consolidate_by_party: bool = False
    compress_context: bool = False
    label: str = "launch"

    def with_change(self, **kwargs) -> AgentConfig:
        return replace(self, **kwargs)

    @property
    def changes(self) -> list[str]:
        return [
            name
            for name in (
                "explain_before_escalate",
                "evidence_for_close",
                "consolidate_by_party",
                "compress_context",
            )
            if getattr(self, name)
        ]


def system_prompt(config: AgentConfig) -> str:
    """The base instructions plus whatever has been approved on top."""
    prompt = SYSTEM_PROMPT
    if config.explain_before_escalate:
        prompt += EXPLAIN_BEFORE_ESCALATE
    if config.evidence_for_close:
        prompt += EVIDENCE_FOR_CLOSE
    if config.consolidate_by_party:
        prompt += CONSOLIDATION_NOTE
    return prompt


def party_index(corpus: list[Alert]) -> dict[str, list[Alert]]:
    """Alerts grouped by the party they concern."""
    index: dict[str, list[Alert]] = {}
    for alert in corpus:
        index.setdefault(alert.party.number, []).append(alert)
    return index


def related_block(alert: Alert, index: dict[str, list[Alert]]) -> str:
    """The party's other alerts, as context for this one."""
    siblings = [a for a in index.get(alert.party.number, []) if a.alert_id != alert.alert_id]
    if not siblings:
        return ""
    lines = [
        f"  {s.alert_id} | {s.scenario} {s.description} | {s.triggered}"
        for s in siblings
    ]
    return (
        f"\n\nOTHER ALERTS ON THIS PARTY ({len(siblings)})\n" + "\n".join(lines)
    )


def case_count(corpus: list[Alert]) -> int:
    """How many human reviews consolidation actually buys.

    Alerts on one party roll into one case, which is how the source system
    behaves: the extract carries 35 alerts across 25 cases.
    """
    return len({a.party.number for a in corpus})
