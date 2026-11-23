"""Choose a model, pay for it, and write down what happened.

The policy is deliberately plain: the cheapest serving model that clears the
quality floor, with the rest of the chain held in reserve for failures. Smarter
routing is a change the Improve pillar has to propose, measure and get approved
- not something asserted here.
"""

from __future__ import annotations

import uuid

from aml.core.ledger import Ledger
from aml.llm.bedrock import BedrockProvider, Completion, ProviderError
from aml.llm.fleet import ModelSpec, load_fleet, serving


class BudgetExceeded(RuntimeError):
    """The run hit its spend cap and stopped rather than quietly overspending."""


class NoEligibleModel(RuntimeError):
    """No serving model clears the requested quality floor."""


class Router:
    """Routes one call at a time and records every attempt."""

    def __init__(
        self,
        ledger: Ledger,
        provider: BedrockProvider | None = None,
        fleet: list[ModelSpec] | None = None,
        spend_cap_usd: float = 5.00,
        run_id: str | None = None,
    ) -> None:
        self.ledger = ledger
        self.provider = provider or BedrockProvider()
        self.fleet = fleet or load_fleet()
        self.spend_cap_usd = spend_cap_usd
        self.run_id = run_id or uuid.uuid4().hex[:8]
        self.down: set[str] = set()

    def chain(self, quality_floor: float) -> list[ModelSpec]:
        """Eligible models, cheapest first."""
        eligible = [m for m in serving(self.fleet) if m.quality >= quality_floor]
        if not eligible:
            raise NoEligibleModel(
                f"no serving model reaches quality {quality_floor}"
            )
        return eligible

    def complete(
        self,
        alert_id: str,
        system: str,
        prompt: str,
        quality_floor: float = 0.0,
        max_tokens: int = 2000,
        pin: str | None = None,
    ) -> tuple[Completion, ModelSpec]:
        """Call the cheapest eligible model, falling through on provider errors."""
        if self.ledger.cost_usd >= self.spend_cap_usd:
            raise BudgetExceeded(
                f"spend cap ${self.spend_cap_usd:.2f} reached at "
                f"${self.ledger.cost_usd:.4f}"
            )

        candidates = self.chain(quality_floor)
        if pin:
            candidates = [m for m in candidates if m.tier == pin] or candidates

        last: ProviderError | None = None
        for attempt, spec in enumerate(candidates, start=1):
            if spec.model in self.down:
                continue
            try:
                completion = self.provider.complete(
                    spec, system, prompt, max_tokens=max_tokens
                )
            except ProviderError as exc:
                last = exc
                self._record(alert_id, spec, None, "error", attempt)
                continue
            self._record(alert_id, spec, completion, "ok", attempt)
            return completion, spec

        raise ProviderError(f"every eligible model failed: {last}")

    def _record(
        self,
        alert_id: str,
        spec: ModelSpec,
        completion: Completion | None,
        status: str,
        attempt: int,
    ) -> None:
        self.ledger.record_call(
            run_id=self.run_id,
            alert_id=alert_id,
            tier=spec.tier,
            provider=spec.provider,
            model=spec.model,
            tokens_in=completion.tokens_in if completion else 0,
            tokens_out=completion.tokens_out if completion else 0,
            tokens_cached=completion.tokens_cached if completion else 0,
            cost_usd=(
                spec.cost(
                    completion.tokens_in,
                    completion.tokens_out,
                    completion.tokens_cached,
                )
                if completion
                else 0.0
            ),
            latency_ms=completion.latency_ms if completion else 0,
            status=status,
            attempt=attempt,
            provenance="live",
        )
