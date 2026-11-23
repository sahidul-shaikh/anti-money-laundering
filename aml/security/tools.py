"""What the agent is allowed to do, and what nothing can grant it.

An agent that can close an alert is, by construction, a laundering tool if it
can be steered. So the destructive scopes are not merely ungranted - they
cannot be granted. A compromised prompt, a persuaded operator and a bug all
hit the same wall.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# No caller, no configuration and no operator may hold these. They exist in the
# registry only so that an attempt to use one is refused loudly and recorded.
UNGRANTABLE = frozenset(
    {
        "alert.close",
        "case.delete",
        "payment.release",
        "watchlist.write",
        "party.write",
        "sar.file",
    }
)


class ToolDenied(PermissionError):
    """The agent asked for a scope it does not hold."""


class ScopeUngrantable(PermissionError):
    """Something tried to grant a scope that may never be held."""


@dataclass
class ToolRegistry:
    """Deny by default. Every call and every refusal is recorded."""

    granted: set[str] = field(default_factory=set)
    handlers: dict[str, Callable[..., object]] = field(default_factory=dict)
    log: list[tuple[str, str]] = field(default_factory=list)

    def register(self, scope: str, handler: Callable[..., object]) -> None:
        self.handlers[scope] = handler

    def grant(self, scope: str) -> None:
        if scope in UNGRANTABLE:
            self.log.append((scope, "grant-refused"))
            raise ScopeUngrantable(
                f"{scope} may never be granted to an automated investigator"
            )
        self.granted.add(scope)
        self.log.append((scope, "granted"))

    def call(self, scope: str, **kwargs) -> object:
        if scope in UNGRANTABLE:
            self.log.append((scope, "denied-ungrantable"))
            raise ToolDenied(f"{scope} is ungrantable")
        if scope not in self.granted:
            self.log.append((scope, "denied-ungranted"))
            raise ToolDenied(f"{scope} not granted")
        if scope not in self.handlers:
            self.log.append((scope, "denied-unimplemented"))
            raise ToolDenied(f"{scope} has no handler")
        self.log.append((scope, "called"))
        return self.handlers[scope](**kwargs)

    def refusals(self) -> list[tuple[str, str]]:
        return [entry for entry in self.log if entry[1].startswith(("denied", "grant-refused"))]


def investigator_registry() -> ToolRegistry:
    """The scopes an L1 investigator agent legitimately needs: all read-only."""
    registry = ToolRegistry()
    for scope in ("party.read", "account.read", "transaction.read", "case.read"):
        registry.register(scope, lambda **kw: {"ok": True})
        registry.grant(scope)
    # Registered so a call is refused by policy rather than by absence.
    for scope in UNGRANTABLE:
        registry.register(scope, lambda **kw: {"ok": True})
    return registry
