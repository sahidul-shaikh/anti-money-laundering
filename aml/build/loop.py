"""Goal, act, verify, iterate.

The loop the deck asks for, with a real oracle on the other side of it. A
stage that produces code does not pass because it says it has finished; it
passes because a test suite it never saw agrees. When the suite disagrees,
its output is handed back and the stage tries again.

Three attempts, then the build stops. An agent that cannot satisfy a fixed
contract in three goes is not going to satisfy it in thirty, and the point of
a gate is that it eventually says no.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

MAX_ATTEMPTS = 3


@dataclass
class Attempt:
    number: int
    produced: list[str]
    outcome: str
    detail: str
    cost_usd: float = 0.0
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "produced": self.produced,
            "outcome": self.outcome,
            "detail": self.detail,
            "cost_usd": round(self.cost_usd, 5),
            "duration_s": round(self.duration_s, 1),
        }


@dataclass
class LoopResult:
    passed: bool
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.attempts)

    @property
    def iterations(self) -> int:
        return len(self.attempts)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "iterations": self.iterations,
            "cost_usd": round(self.cost_usd, 5),
            "attempts": [a.to_dict() for a in self.attempts],
        }


def run_loop(
    act: Callable[[str | None], tuple[list[str], float, float]],
    verify: Callable[[], tuple[bool, str]],
    max_attempts: int = MAX_ATTEMPTS,
    feedback: Callable[[str], str] | None = None,
    on_attempt: Callable[[Attempt], None] | None = None,
) -> LoopResult:
    """Act, verify, and iterate with the verifier's own output as the feedback.

    `act` receives the previous failure (None on the first attempt) and returns
    what it produced, its cost and its duration. `verify` returns whether the
    work is acceptable and why.
    """
    result = LoopResult(passed=False)
    previous: str | None = None

    for number in range(1, max_attempts + 1):
        produced, cost, duration = act(previous)
        ok, detail = verify()
        attempt = Attempt(
            number=number,
            produced=produced,
            outcome="pass" if ok else "fail",
            detail=detail,
            cost_usd=cost,
            duration_s=duration,
        )
        result.attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt)
        if ok:
            result.passed = True
            return result
        previous = feedback(detail) if feedback else detail

    return result
