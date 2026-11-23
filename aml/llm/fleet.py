"""Model fleet: the tiers the router may choose between, and what each costs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

FLEET_CONFIG = Path(__file__).with_name("fleet.json")

# What a provider charges to read a cached prompt prefix, as a fraction of the
# normal input rate. Bedrock does not bill cached reads on every model in this
# fleet; the router records cached tokens as zero until a model that supports
# it is in play, so this rate is inert rather than assumed.
CACHE_READ_RATE = 0.10


@dataclass(frozen=True)
class ModelSpec:
    """One model in the fleet: its tier, its price and the quality it is trusted for."""

    tier: str
    provider: str
    model: str
    price_in: float
    price_out: float
    quality: float
    quality_basis: str
    latency_ms: int
    serving: bool

    def cost(self, tokens_in: int, tokens_out: int, tokens_cached: int = 0) -> float:
        """USD for a call of this size, from per-million-token prices."""
        billable_in = (tokens_in - tokens_cached) + tokens_cached * CACHE_READ_RATE
        return (billable_in * self.price_in + tokens_out * self.price_out) / 1_000_000


def load_fleet(name: str | None = None) -> list[ModelSpec]:
    """Load a named fleet, or the one marked active in the config."""
    config = json.loads(FLEET_CONFIG.read_text())
    name = name or config["active_fleet"]
    return [
        ModelSpec(tier=tier, **spec)
        for tier, spec in config["fleets"][name].items()
        if not tier.startswith("_")
    ]


def serving(fleet: list[ModelSpec]) -> list[ModelSpec]:
    """The models the router is allowed to select, cheapest first."""
    return sorted(
        (m for m in fleet if m.serving), key=lambda m: m.price_in + m.price_out
    )
