"""Does the artifact contain what the phase was required to produce?

Two kinds of requirement, because they fail differently.

A *section* must appear as a heading. Searching the whole document for the
phrase is not good enough: a specification that says "a threat model will be
produced in due course" contains the words and none of the content, and an
evaluator that accepts it is theatre.

A *token* is an identifier - AC-1, T-1 - that belongs in running text, so for
those a plain search is the right test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from aml.build.phases import PhaseSpec

MIN_LENGTH = 400

# Markdown headings, bold run-in headings, and numbered variants of both.
HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s+|\*\*|\d+[.)]\s*\*{0,2})(.+)$", re.M)


@dataclass(frozen=True)
class Evaluation:
    phase_id: str
    passed: bool
    missing: tuple[str, ...]
    length: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "passed": self.passed,
            "missing": list(self.missing),
            "length": self.length,
            "reason": self.reason,
        }


def headings(artifact: str) -> list[str]:
    return [m.group(1).upper() for m in HEADING.finditer(artifact)]


def evaluate(phase: PhaseSpec, artifact: str) -> Evaluation:
    found = headings(artifact)
    body = artifact.upper()

    missing = tuple(
        marker for marker in phase.markers
        if not any(marker.upper() in heading for heading in found)
    ) + tuple(
        token for token in phase.tokens if token.upper() not in body
    )

    if len(artifact) < MIN_LENGTH:
        return Evaluation(
            phase.phase_id, False, missing, len(artifact),
            f"artifact is {len(artifact)} characters, below the {MIN_LENGTH} "
            f"minimum for a reviewable document",
        )
    if missing:
        return Evaluation(
            phase.phase_id, False, missing, len(artifact),
            "required section missing: " + ", ".join(missing),
        )
    return Evaluation(
        phase.phase_id, True, (), len(artifact),
        f"all {len(phase.markers)} sections and {len(phase.tokens)} identifiers present",
    )
