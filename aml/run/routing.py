"""Route one alert, check the answer, and escalate when the evidence is absent.

The Router is the *mechanism*: the cheapest serving model above a quality
floor, provider fallback, a spend cap, and a ledger entry for every attempt.
This module is the *policy*: what to do when a cheap model answers but cannot
show its working.

The policy is named and parameterised deliberately. On the recorded baseline
the cheap tier returned no citable evidence on 12 of 61 clean alerts, and was
wrong on 67% of those against a 22% base rate - so "answered with nothing to
point at" is a real signal, computed from the answer itself with no label and
no judge model. Changing the policy is a proposal the Improve pillar has to
measure and approve, not something asserted here.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from aml.corpus.model import Alert
from aml.corpus.render import render
from aml.llm.bedrock import BedrockProvider, ProviderError
from aml.llm.fleet import ModelSpec, load_fleet, serving
from aml.llm.router import Router
from aml.run.config import AgentConfig, system_prompt
from aml.run.prompts import user_turn
from aml.run.verdict import Grade, Unparseable, Verdict, grade, parse

BROKEN_MODEL = "meta.llama3-3-70b-instruct-v9:0"


@dataclass(frozen=True)
class RoutingPolicy:
    """When to start cheap, and when to stop trusting the cheap answer."""

    quality_floor: float = 0.0
    escalate_without_evidence: bool = True
    min_groundedness: float = 1.0
    max_escalations: int = 1
    label: str = "evidence-gated"

    def describe(self) -> str:
        if not self.escalate_without_evidence:
            return "take the cheapest answer above the quality floor, whatever it says"
        return (
            "start at the cheapest model above the quality floor; escalate once "
            "if the answer cites no evidence, or cites a reference that is not "
            "in the alert"
        )


@dataclass(frozen=True)
class Reference:
    """One citation, and whether the alert actually contains it."""

    ref: str
    in_alert: bool


@dataclass(frozen=True)
class EvidenceCheck:
    """Is this answer backed by transactions that exist in this alert?"""

    passed: bool
    reason: str
    cited: int
    invented: int
    groundedness: float
    references: tuple[Reference, ...] = ()


@dataclass
class Attempt:
    """One model call: what went out, what came back, and how it scored."""

    n: int
    tier: str
    model: str
    quality: float
    system: str
    prompt: str
    response: str = ""
    verdict: Verdict | None = None
    grade: Grade | None = None
    check: EvidenceCheck | None = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "tier": self.tier,
            "model": self.model,
            "quality": self.quality,
            "system_chars": len(self.system),
            "prompt_chars": len(self.prompt),
            "system": self.system,
            "prompt": self.prompt,
            "response": self.response,
            "disposition": self.verdict.disposition if self.verdict else None,
            "confidence": self.verdict.confidence if self.verdict else None,
            "typology": self.verdict.typology if self.verdict else None,
            "narrative": self.verdict.narrative if self.verdict else "",
            "risk_score": self.verdict.risk_score if self.verdict else None,
            "check": {
                "passed": self.check.passed,
                "reason": self.check.reason,
                "cited": self.check.cited,
                "invented": self.check.invented,
                "groundedness": round(self.check.groundedness, 4),
                "references": [
                    {"ref": r.ref, "in_alert": r.in_alert} for r in self.check.references
                ],
            } if self.check else None,
            "correct": self.grade.correct if self.grade else None,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "error": self.error,
        }


@dataclass
class RoutedResult:
    """The whole journey for one alert."""

    alert_id: str
    policy: RoutingPolicy
    attempts: list[Attempt] = field(default_factory=list)
    escalated: bool = False

    @property
    def final(self) -> Attempt | None:
        answered = [a for a in self.attempts if a.verdict]
        return answered[-1] if answered else None

    @property
    def cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.attempts)

    def to_dict(self) -> dict:
        final = self.final
        return {
            "alert_id": self.alert_id,
            "policy": {
                "label": self.policy.label,
                "quality_floor": self.policy.quality_floor,
                "describe": self.policy.describe(),
            },
            "attempts": [a.to_dict() for a in self.attempts],
            "escalated": self.escalated,
            "final_tier": final.tier if final else None,
            "final_disposition": final.verdict.disposition if final and final.verdict else None,
            "correct": final.grade.correct if final and final.grade else None,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": sum(a.latency_ms for a in self.attempts),
        }


@dataclass(frozen=True)
class RouteEvent:
    """Something worth showing while the routing happens."""

    kind: str
    text: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "data": self.data}


def check_evidence(
    verdict: Verdict, alert: Alert, policy: RoutingPolicy
) -> EvidenceCheck:
    """Tick every cited reference against the alert's own transaction list.

    Deterministic. No model is asked whether the answer is good.
    """
    cited = verdict.cited_refs
    references = tuple(Reference(ref, ref in alert.refs) for ref in cited)
    invented = [r for r in references if not r.in_alert]
    groundedness = 0.0 if not cited else (len(cited) - len(invented)) / len(cited)

    if not cited:
        return EvidenceCheck(
            False, "the answer cites no transactions at all", 0, 0, 0.0, references
        )
    if groundedness < policy.min_groundedness:
        return EvidenceCheck(
            False,
            f"{len(invented)} of {len(cited)} cited references are not in this alert",
            len(cited), len(invented), groundedness, references,
        )
    return EvidenceCheck(
        True,
        f"all {len(cited)} cited references exist in this alert",
        len(cited), 0, groundedness, references,
    )


def break_tier(fleet: list[ModelSpec], tier: str) -> list[ModelSpec]:
    """Point one tier at a model id that does not exist.

    Fault injection for demonstrating the fallback chain. The call genuinely
    fails at Bedrock - nothing here is simulated - and the router moves on to
    the next eligible model.
    """
    return [
        replace(spec, model=BROKEN_MODEL) if spec.tier == tier else spec
        for spec in fleet
    ]


def route_alert(
    alert: Alert,
    policy: RoutingPolicy | None = None,
    agent: AgentConfig | None = None,
    router: Router | None = None,
    fleet: list[ModelSpec] | None = None,
    max_tokens: int = 2000,
) -> Iterator[RouteEvent]:
    """Route one alert, yielding what happened as it happens.

    The last event is always ``final`` and carries the whole result.
    """
    policy = policy or RoutingPolicy()
    agent = agent or AgentConfig()
    fleet = fleet or load_fleet()
    router = router or Router(ledger=_ledger(), fleet=fleet)
    router.fleet = fleet

    chain = [m for m in serving(fleet) if m.quality >= policy.quality_floor]
    if not chain:
        yield RouteEvent("error", f"no serving model reaches quality {policy.quality_floor}")
        return

    system = system_prompt(agent)
    prompt = user_turn(alert, render(alert))
    result = RoutedResult(alert_id=alert.alert_id, policy=policy)

    yield RouteEvent(
        "decision",
        f"{len(chain)} of {len(fleet)} models are eligible; starting at {chain[0].tier}",
        {
            "policy": policy.label,
            "describe": policy.describe(),
            "quality_floor": policy.quality_floor,
            "chain": [
                {"tier": m.tier, "model": m.model, "quality": m.quality,
                 "price_in": m.price_in, "price_out": m.price_out}
                for m in chain
            ],
            "fleet": [
                {"tier": m.tier, "model": m.model, "quality": m.quality,
                 "serving": m.serving, "price_in": m.price_in, "price_out": m.price_out}
                for m in fleet
            ],
            "alert_id": alert.alert_id,
            "label": alert.label,
            "scenario": alert.scenario,
            "refs": list(alert.refs),
        },
    )

    yield RouteEvent(
        "prompt",
        f"{len(system):,} characters of system prompt, {len(prompt):,} of alert",
        {"system": system, "prompt": prompt,
         "system_chars": len(system), "prompt_chars": len(prompt)},
    )

    for index, spec in enumerate(chain[: policy.max_escalations + 1]):
        attempt = Attempt(
            n=index + 1, tier=spec.tier, model=spec.model, quality=spec.quality,
            system=system, prompt=prompt,
        )
        result.attempts.append(attempt)
        yield RouteEvent(
            "calling", f"calling the {spec.tier} tier",
            {"n": attempt.n, "tier": spec.tier, "model": spec.model},
        )

        try:
            completion, used = router.complete(
                alert_id=alert.alert_id, system=system, prompt=prompt,
                quality_floor=policy.quality_floor, max_tokens=max_tokens,
                pin=spec.tier,
            )
        except ProviderError as exc:
            attempt.error = str(exc)[:300]
            yield RouteEvent(
                "provider_error",
                f"the {spec.tier} tier failed: {attempt.error[:120]}",
                {"n": attempt.n, "tier": spec.tier, "error": attempt.error},
            )
            continue

        attempt.tier, attempt.model = used.tier, used.model
        attempt.response = completion.text
        attempt.tokens_in = completion.tokens_in
        attempt.tokens_out = completion.tokens_out
        attempt.latency_ms = completion.latency_ms
        attempt.cost_usd = used.cost(
            completion.tokens_in, completion.tokens_out, completion.tokens_cached
        )

        yield RouteEvent(
            "answer",
            f"{used.tier} answered in {completion.latency_ms} ms",
            {"n": attempt.n, "tier": used.tier, "response": completion.text,
             "tokens_in": completion.tokens_in, "tokens_out": completion.tokens_out,
             "latency_ms": completion.latency_ms,
             "cost_usd": round(attempt.cost_usd, 6)},
        )

        try:
            attempt.verdict = parse(completion.text)
        except Unparseable as exc:
            attempt.error = f"unparseable: {exc}"
            yield RouteEvent("unparseable", attempt.error, {"n": attempt.n})
            continue

        attempt.grade = grade(attempt.verdict, alert)
        attempt.check = check_evidence(attempt.verdict, alert, policy)
        yield RouteEvent(
            "check",
            attempt.check.reason,
            {"n": attempt.n, "tier": used.tier,
             "disposition": attempt.verdict.disposition,
             "confidence": attempt.verdict.confidence,
             "correct": attempt.grade.correct,
             "check": attempt.to_dict()["check"]},
        )

        if attempt.check.passed or not policy.escalate_without_evidence:
            break
        if index + 1 <= policy.max_escalations and index + 1 < len(chain):
            result.escalated = True
            yield RouteEvent(
                "escalate",
                f"escalating to {chain[index + 1].tier}: {attempt.check.reason}",
                {"from": used.tier, "to": chain[index + 1].tier,
                 "reason": attempt.check.reason},
            )

    yield RouteEvent("final", "routing finished", result.to_dict())


def _ledger():
    from aml.core.ledger import Ledger

    return Ledger()
