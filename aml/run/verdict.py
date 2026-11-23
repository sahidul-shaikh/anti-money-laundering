"""Parse a model response into a verdict, then grade it.

Groundedness is computed, not judged: a cited transaction reference either
appears in the alert or it does not. No second model is involved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from aml.corpus.model import Alert

DISPOSITIONS = {
    "escalate_to_case",
    "close_no_further_action",
    "insufficient_information",
}

REQUIRED = ("disposition", "evidence", "narrative", "risk_score")


class Unparseable(ValueError):
    """The response was not a JSON object we can score."""


@dataclass(frozen=True)
class Verdict:
    disposition: str
    typology: str | None
    risk_score: int
    confidence: float
    evidence: tuple[dict, ...]
    narrative: str
    open_questions: tuple[str, ...]
    regulatory_flags: tuple[str, ...]
    score_factors: tuple[dict, ...]
    missing_fields: tuple[str, ...] = ()

    @property
    def cited_refs(self) -> list[str]:
        return [
            str(ref)
            for item in self.evidence
            for ref in (item.get("transaction_refs") or [])
        ]


@dataclass(frozen=True)
class Grade:
    correct: bool
    groundedness: float
    cited: int
    invented: int
    complete: bool
    notes: tuple[str, ...] = field(default=())


def parse(text: str) -> Verdict:
    """Pull the JSON object out of a response and coerce it into a Verdict."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise Unparseable("no JSON object in response")
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise Unparseable(str(exc)) from exc
    if not isinstance(raw, dict):
        raise Unparseable("response JSON is not an object")

    disposition = str(raw.get("disposition", "")).strip()
    if disposition not in DISPOSITIONS:
        raise Unparseable(f"unknown disposition {disposition!r}")

    evidence = raw.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []

    return Verdict(
        disposition=disposition,
        typology=raw.get("typology"),
        risk_score=_as_int(raw.get("risk_score")),
        confidence=_as_float(raw.get("confidence")),
        evidence=tuple(e for e in evidence if isinstance(e, dict)),
        narrative=str(raw.get("narrative") or ""),
        open_questions=tuple(str(q) for q in (raw.get("open_questions") or [])),
        regulatory_flags=tuple(str(f) for f in (raw.get("regulatory_flags") or [])),
        score_factors=tuple(
            f for f in (raw.get("score_factors") or []) if isinstance(f, dict)
        ),
        missing_fields=tuple(k for k in REQUIRED if k not in raw),
    )


def grade(verdict: Verdict, alert: Alert) -> Grade:
    """Score one verdict against the alert it came from."""
    cited = verdict.cited_refs
    invented = [ref for ref in cited if ref not in alert.refs]
    notes = []

    if not cited:
        groundedness = 0.0
        notes.append("no evidence cited")
    else:
        groundedness = (len(cited) - len(invented)) / len(cited)
    if invented:
        notes.append(f"{len(invented)} invented references")

    complete = not verdict.missing_fields and bool(verdict.narrative.strip())
    if verdict.missing_fields:
        notes.append("missing " + ",".join(verdict.missing_fields))

    return Grade(
        correct=verdict.disposition == alert.label,
        groundedness=groundedness,
        cited=len(cited),
        invented=len(invented),
        complete=complete,
        notes=tuple(notes),
    )


def _as_int(value: object) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
