"""Run the corpus through the agent and record what happened."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from aml.corpus.model import Alert
from aml.corpus.render import render
from aml.core.ledger import Ledger, handling_cost_gbp
from aml.llm.bedrock import ProviderError
from aml.llm.router import Router
from aml.run.config import AgentConfig, party_index, related_block, system_prompt
from aml.run.prompts import user_turn
from aml.run.verdict import Grade, Unparseable, Verdict, grade, parse

# An infrastructure failure and a malformed answer are different things, and
# conflating them would flatter the agent in one direction and damn it in the
# other. They stay separate all the way to the telemetry.
UNPARSEABLE = "unparseable"
PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class RunConfig:
    """What the estate is set to for one run."""

    quality_floor: float = 0.0
    pin: str | None = None
    workers: int = 8
    max_tokens: int = 2000
    spend_cap_usd: float = 5.00
    label: str = "baseline"
    agent: AgentConfig = AgentConfig()


@dataclass
class Disposition:
    """One alert, what the agent said, and how it scored."""

    alert: Alert
    verdict: Verdict | None
    grade: Grade
    tier: str
    cost_usd: float
    latency_ms: int
    error: str = ""


def run_alert(
    alert: Alert,
    router: Router,
    config: RunConfig,
    index: dict[str, list[Alert]] | None = None,
) -> Disposition:
    rendered = render(alert)
    if config.agent.consolidate_by_party and index:
        rendered += related_block(alert, index)
    try:
        completion, spec = router.complete(
            alert_id=alert.alert_id,
            system=system_prompt(config.agent),
            prompt=user_turn(alert, rendered),
            quality_floor=config.quality_floor,
            max_tokens=config.max_tokens,
            pin=config.pin or config.agent.tier,
        )
    except ProviderError as exc:
        return Disposition(
            alert=alert,
            verdict=None,
            grade=Grade(False, 0.0, 0, 0, False, ("provider error",)),
            tier="none",
            cost_usd=0.0,
            latency_ms=0,
            error=str(exc)[:160],
        )

    cost = spec.cost(completion.tokens_in, completion.tokens_out, completion.tokens_cached)
    try:
        verdict = parse(completion.text)
    except Unparseable as exc:
        return Disposition(
            alert=alert,
            verdict=None,
            grade=Grade(False, 0.0, 0, 0, False, (f"unparseable: {exc}",)),
            tier=spec.tier,
            cost_usd=cost,
            latency_ms=completion.latency_ms,
            error=str(exc)[:160],
        )

    return Disposition(
        alert=alert,
        verdict=verdict,
        grade=grade(verdict, alert),
        tier=spec.tier,
        cost_usd=cost,
        latency_ms=completion.latency_ms,
    )


def run_corpus(
    corpus: list[Alert],
    config: RunConfig | None = None,
    ledger: Ledger | None = None,
    router: Router | None = None,
) -> tuple[Ledger, list[Disposition]]:
    """Disposition every alert, concurrently, and write the ledger."""
    config = config or RunConfig()
    ledger = ledger or Ledger()
    router = router or Router(ledger, spend_cap_usd=config.spend_cap_usd)

    index = party_index(corpus) if config.agent.consolidate_by_party else None
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        dispositions = list(
            pool.map(lambda a: run_alert(a, router, config, index), corpus)
        )

    # Alerts on one party roll into one case, so one escalation buys one
    # review for the whole party rather than one per alert.
    share = _review_share(corpus) if config.agent.consolidate_by_party else {}

    for item in dispositions:
        if item.verdict:
            disposition = item.verdict.disposition
        else:
            disposition = PROVIDER_ERROR if item.tier == "none" else UNPARSEABLE
        ledger.record_outcome(
            run_id=router.run_id,
            alert_id=item.alert.alert_id,
            provenance=item.alert.provenance,
            scenario=item.alert.scenario,
            label=item.alert.label,
            disposition=disposition,
            correct=item.grade.correct,
            groundedness=item.grade.groundedness,
            cited=item.grade.cited,
            invented=item.grade.invented,
            confidence=item.verdict.confidence if item.verdict else 0.0,
            tier=item.tier,
            cost_usd=item.cost_usd,
            handling_cost_gbp=handling_cost_gbp(
                disposition,
                item.grade.correct,
                item.cost_usd,
                review_share=share.get(item.alert.party.number, 1.0),
            ),
        )
    return ledger, dispositions


def _review_share(corpus: list[Alert]) -> dict[str, float]:
    """A party's single review, divided across the alerts that triggered it."""
    index = party_index(corpus)
    return {number: 1.0 / len(alerts) for number, alerts in index.items()}
