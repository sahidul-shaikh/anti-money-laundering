"""Ask the agent about one alert, typed or pasted by a person.

The batch engine dispositions seventy alerts at a time. This is the single-turn
version a presenter can drive by hand: paste an alert, see exactly what is sent,
send it, and read what came back.

Two things make it honest rather than a toy. The prompt is assembled by the same
code the batch run uses, so what you see is what the agent gets. And where the
pasted text names an alert the harness knows, the answer is scored against the
real label; where it does not, the console says the answer is unscored instead
of inventing a verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aml.corpus.model import Alert
from aml.corpus.render import render
from aml.llm.fleet import ModelSpec, load_fleet, serving
from aml.llm.router import Router
from aml.run.prompts import SYSTEM_PROMPT, user_turn
from aml.run.routing import break_tier
from aml.run.rules import for_scenario
from aml.run.verdict import Unparseable, grade, parse
from aml.security.envelope import CLOSE, OPEN, PREAMBLE
from aml.security.injection import judge
from aml.security.swarm import with_payload

ALERT_ID = re.compile(r"\bALERT\s+([A-Z]?\d{4,6})\b", re.I)
SCENARIO = re.compile(r"\b(SAS\d{5})\b")


@dataclass
class Exchange:
    """One question put to the agent, and everything behind the answer."""

    tier: str = ""
    model: str = ""
    system: str = ""
    prompt: str = ""
    response: str = ""
    disposition: str | None = None
    confidence: float | None = None
    narrative: str = ""
    cited: list[str] = field(default_factory=list)
    verified: list[dict] = field(default_factory=list)
    groundedness: float | None = None
    correct: bool | None = None
    expected: str | None = None
    matched_alert: str | None = None
    scenario: str | None = None
    rule: dict | None = None
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def find_alert(text: str, corpus: list[Alert]) -> Alert | None:
    """The corpus alert this text is about, if the harness knows it."""
    match = ALERT_ID.search(text)
    if match:
        wanted = match.group(1).upper()
        for alert in corpus:
            if alert.alert_id.upper() == wanted:
                return alert
    return None


def _spec(tier: str) -> ModelSpec:
    fleet = serving(load_fleet())
    return next((m for m in fleet if m.tier == tier), fleet[0])


def ask(
    text: str,
    corpus: list[Alert],
    router: Router,
    tier: str = "premium",
    max_tokens: int = 1600,
) -> Exchange:
    """Put pasted alert text to the agent exactly as the batch run would."""
    alert = find_alert(text, corpus)
    scenario = (alert.scenario if alert
                else (SCENARIO.search(text).group(1) if SCENARIO.search(text) else None))

    exchange = Exchange(
        tier=tier, system=SYSTEM_PROMPT,
        matched_alert=alert.alert_id if alert else None,
        scenario=scenario,
        expected=alert.label if alert else None,
    )

    # The rule block comes from the catalogue either way; when the paste is not
    # a known alert we still retrieve by whatever scenario code it mentions.
    spec_rule = for_scenario(scenario) if scenario else None
    exchange.rule = spec_rule.to_dict() if spec_rule else None
    if alert:
        exchange.prompt = user_turn(alert, render(alert))
        exchange.note = f"recognised alert {alert.alert_id}; scored against the harness"
    else:
        rule_block = spec_rule.render() if spec_rule else (
            "THE DETECTION RULE THIS ALERT FIRED\n\n"
            "No scenario code was recognised in this text, so no rule was "
            "retrieved. Do not assume a threshold."
        )
        exchange.prompt = (
            f"{rule_block}\n\n{text.strip()}\n\n"
            "Disposition this alert. Return the JSON object only."
        )
        exchange.note = "not a corpus alert - the answer is shown but not scored"

    return _send(exchange, router, tier, alert, max_tokens)


def attack(
    text: str,
    payload_text: str,
    corpus: list[Alert],
    router: Router,
    tier: str = "cheap",
    guardrail: bool = True,
    probe_id: str = "P-01",
    max_tokens: int = 1600,
    prompt_only: bool = False,
) -> Exchange:
    """The same question with attacker-controlled text in the reference field."""
    alert = find_alert(text, corpus)
    exchange = Exchange(
        tier=tier, system=SYSTEM_PROMPT,
        matched_alert=alert.alert_id if alert else None,
        scenario=alert.scenario if alert else None,
        expected=alert.label if alert else None,
    )

    if alert:
        from aml.security.injection import Payload

        poisoned = with_payload(
            alert, Payload(probe_id, "pasted", payload_text, "pasted by the presenter"))
        exchange.prompt = user_turn(poisoned, render(poisoned, guardrail=guardrail))
        exchange.note = (
            f"payload placed in the reference text of transaction "
            f"{poisoned.transactions[0].ref}"
        )
    else:
        # Nothing to attach the payload to, so append it framed exactly as the
        # envelope would - or not framed at all. The comparison still holds.
        if guardrail:
            block = f"\n{PREAMBLE}\n{OPEN}\n  pasted: {payload_text}\n{CLOSE}"
        else:
            block = f"\nPAYMENT REFERENCES\n  pasted: {payload_text}"
        exchange.prompt = (
            f"{text.strip()}{block}\n\n"
            "Disposition this alert. Return the JSON object only."
        )
        exchange.note = "not a corpus alert - unscored, and the attack is appended"

    if prompt_only:
        # The console shows the assembled prompt first and sends on a second
        # press, so the audience sees what goes in before anything comes back.
        exchange.model = _spec(tier).model
        return exchange
    return _send(exchange, router, tier, alert, max_tokens, probe_id, payload_text)


def _send(
    exchange: Exchange,
    router: Router,
    tier: str,
    alert: Alert | None,
    max_tokens: int,
    probe_id: str = "",
    payload_text: str = "",
) -> Exchange:
    spec = _spec(tier)
    exchange.model = spec.model
    try:
        completion, used = router.complete(
            alert_id=exchange.matched_alert or "pasted",
            system=exchange.system, prompt=exchange.prompt,
            pin=tier, max_tokens=max_tokens,
        )
    except Exception as exc:  # provider failures are the caller's to show
        exchange.error = f"{type(exc).__name__}: {exc}"[:300]
        return exchange

    exchange.tier, exchange.model = used.tier, used.model
    exchange.response = completion.text
    exchange.latency_ms = completion.latency_ms
    exchange.tokens_in = completion.tokens_in
    exchange.tokens_out = completion.tokens_out
    exchange.cost_usd = round(
        used.cost(completion.tokens_in, completion.tokens_out,
                  completion.tokens_cached), 6)

    try:
        verdict = parse(completion.text)
    except Unparseable as exc:
        exchange.error = f"unparseable: {exc}"
        return exchange

    exchange.disposition = verdict.disposition
    exchange.confidence = verdict.confidence
    exchange.narrative = verdict.narrative
    exchange.cited = verdict.cited_refs

    if alert:
        scored = grade(verdict, alert)
        exchange.correct = scored.correct
        exchange.groundedness = round(scored.groundedness, 4)
        exchange.verified = [
            {"ref": r, "in_alert": r in alert.refs} for r in verdict.cited_refs
        ]
        if probe_id:
            from aml.security.injection import Payload

            outcome = judge(
                Payload(probe_id, "pasted", payload_text, ""),
                verdict, completion.text, alert.label)
            exchange.note = (
                ("EXPLOITED: " if outcome.complied else "DEFENDED: ")
                + outcome.observation
            )
    return exchange


def route(
    text: str, corpus: list[Alert], router: Router, broken: str | None = None,
) -> dict:
    """Run the real routing policy over pasted text.

    Cheapest serving model first. Its answer is checked against the alert's own
    transaction list, and only an answer that cannot show its working is sent
    up to the stronger model. Nothing here picks a tier by hand.
    """
    fleet = load_fleet()
    if broken:
        # A real model id, swapped for one that does not exist. The call still
        # goes to Bedrock; Bedrock is what refuses it.
        fleet = break_tier(fleet, broken)
    router.fleet = fleet
    chain = [m.tier for m in serving(fleet)]
    attempts: list[dict] = []

    for position, tier in enumerate(chain):
        exchange = ask(text, corpus, router, tier=tier)
        cited = len(exchange.cited)
        invented = sum(1 for r in exchange.verified if not r["in_alert"])
        trusted = bool(cited) and invented == 0 and not exchange.error
        reason = (
            exchange.error or
            ("the answer cites no transactions at all" if not cited else
             f"{invented} of {cited} cited references are not in this alert"
             if invented else
             f"all {cited} cited references exist in this alert")
        )
        attempts.append({**exchange.to_dict(), "trusted": trusted,
                         "reason": reason, "n": position + 1})
        if trusted or position + 1 >= len(chain):
            break

    final = attempts[-1]
    return {
        "attempts": attempts,
        "escalated": len(attempts) > 1,
        "chain": chain,
        "final_tier": final["tier"],
        "disposition": final["disposition"],
        "correct": final["correct"],
        "expected": final["expected"],
        "matched_alert": final["matched_alert"],
        "rule": final["rule"],
    }
