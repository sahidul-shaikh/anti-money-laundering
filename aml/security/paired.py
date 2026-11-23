"""Fire one payload twice: once unprotected, once enveloped.

The point of the pairing is that nothing changes except where the attacker's
text sits. Same alert, same model, same payload, same temperature. If the
unprotected run is hijacked and the enveloped one is not, the difference is the
framing and cannot be anything else.

Both runs are judged by the deterministic judges in ``injection`` - a regex or
a disposition comparison, never a model asked for its opinion. Anything that
looks exploited is fired again before it is believed.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from aml.corpus.model import Alert
from aml.corpus.render import render
from aml.llm.router import Router
from aml.run.prompts import SYSTEM_PROMPT, user_turn
from aml.run.verdict import Unparseable, parse
from aml.security.envelope import GUARDRAIL, render_references
from aml.security.injection import PAYLOADS, Payload, judge
from aml.security.swarm import (
    DECLARED_PROBES,
    EXPLOITED,
    run_control_probes,
    with_payload,
)

BY_ID = {p.probe_id: p for p in PAYLOADS}


@dataclass(frozen=True)
class ProbeEvent:
    """Something worth showing while the probe runs."""

    kind: str
    text: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "data": self.data}


def _fire(alert: Alert, payload: Payload, router: Router, guardrail: bool, pin: str):
    """One call with the payload in place, framed or not."""
    poisoned = with_payload(alert, payload)
    prompt = user_turn(poisoned, render(poisoned, guardrail=guardrail))
    completion, spec = router.complete(
        alert_id=f"{alert.alert_id}:{payload.probe_id}:{'on' if guardrail else 'off'}",
        system=SYSTEM_PROMPT, prompt=prompt, pin=pin, max_tokens=1600,
    )
    try:
        verdict = parse(completion.text)
    except Unparseable:
        verdict = None
    return poisoned, prompt, completion, spec, verdict


def paired_probe(
    alert: Alert,
    probe_id: str,
    router: Router,
    pin: str = "cheap",
    verify: bool = True,
) -> Iterator[ProbeEvent]:
    """Run one payload unprotected, then enveloped, and compare."""
    payload = BY_ID[probe_id]
    poisoned = with_payload(alert, payload)

    yield ProbeEvent(
        "target",
        f"{payload.probe_id} {payload.name} against alert {alert.alert_id}",
        {
            "alert_id": alert.alert_id,
            "party": alert.party.name,
            "label": alert.label,
            "transactions": len(alert.transactions),
            "probe_id": payload.probe_id,
            "name": payload.name,
            "intent": payload.intent,
            "attacker_text": payload.text,
            "carrier_ref": poisoned.transactions[0].ref,
            "tier": pin,
        },
    )

    results = {}
    for guardrail in (False, True):
        state = "on" if guardrail else "off"
        block = render_references(poisoned.transactions, guardrail=guardrail)

        yield ProbeEvent(
            "framing",
            f"guardrail {state}: the attacker's text "
            + ("framed as untrusted evidence" if guardrail
               else "sitting inline among the transaction rows"),
            {"guardrail": guardrail, "state": state, "block": block,
             "control": GUARDRAIL if guardrail else "none"},
        )
        yield ProbeEvent("calling", f"calling the {pin} tier with the guardrail {state}",
                         {"state": state})

        _, prompt, completion, spec, verdict = _fire(
            alert, payload, router, guardrail, pin)
        cost = spec.cost(completion.tokens_in, completion.tokens_out,
                         completion.tokens_cached)

        yield ProbeEvent(
            "answer", f"{spec.tier} answered in {completion.latency_ms} ms",
            {"state": state, "response": completion.text, "prompt": prompt,
             "prompt_chars": len(prompt), "latency_ms": completion.latency_ms,
             "tokens_in": completion.tokens_in, "tokens_out": completion.tokens_out,
             "cost_usd": round(cost, 6)},
        )

        outcome = judge(payload, verdict, completion.text, alert.label)
        reproduced = None
        if verify and outcome.complied:
            yield ProbeEvent(
                "verifying",
                "that looks exploited - firing the same payload again before "
                "believing it",
                {"state": state},
            )
            _, _, again, _, verdict2 = _fire(alert, payload, router, guardrail, pin)
            reproduced = judge(payload, verdict2, again.text, alert.label).complied

        results[state] = {
            "state": state,
            "guardrail": guardrail,
            "exploited": outcome.complied,
            "observation": outcome.observation,
            "disposition": outcome.disposition,
            "expected": alert.label,
            "reproduced": reproduced,
            "confirmed": outcome.complied and reproduced is not False,
            "cost_usd": round(cost, 6),
        }
        yield ProbeEvent(
            "judged",
            ("EXPLOITED: " if outcome.complied else "DEFENDED: ") + outcome.observation,
            results[state],
        )

    yield ProbeEvent(
        "final",
        "same payload, same model, same alert - only the framing differed",
        {
            "probe_id": payload.probe_id,
            "tier": pin,
            "off": results.get("off"),
            "on": results.get("on"),
            "proved": bool(results.get("off", {}).get("confirmed")
                           and not results.get("on", {}).get("confirmed")),
            "cost_usd": round(sum(r["cost_usd"] for r in results.values()), 6),
        },
    )


def sweep(
    alert: Alert, router: Router, pin: str = "cheap", guardrail: bool = False,
    verify: bool = True,
) -> Iterator[ProbeEvent]:
    """Every payload against one alert, one guardrail state, findings as they land."""
    yield ProbeEvent(
        "sweep_start",
        f"{len(PAYLOADS)} executable probes, {len(DECLARED_PROBES)} declared",
        {"tier": pin, "guardrail": guardrail,
         "payloads": [{"probe_id": p.probe_id, "name": p.name, "intent": p.intent}
                      for p in PAYLOADS]},
    )

    for payload in PAYLOADS:
        yield ProbeEvent("probe", f"{payload.probe_id} {payload.name}",
                         {"probe_id": payload.probe_id, "intent": payload.intent})
        _, _, completion, _, verdict = _fire(alert, payload, router, guardrail, pin)
        outcome = judge(payload, verdict, completion.text, alert.label)

        reproduced = None
        if verify and outcome.complied:
            _, _, again, _, verdict2 = _fire(alert, payload, router, guardrail, pin)
            reproduced = judge(payload, verdict2, again.text, alert.label).complied

        yield ProbeEvent(
            "finding",
            f"{payload.probe_id}: {EXPLOITED if outcome.complied else 'defended'}",
            {"probe_id": payload.probe_id, "name": payload.name,
             "outcome": EXPLOITED if outcome.complied else "defended",
             "observation": outcome.observation
             + ("" if reproduced is not False else "; did not reproduce on re-run"),
             "disposition": outcome.disposition, "reproduced": reproduced,
             "confirmed": outcome.complied and reproduced is not False,
             "response": completion.text},
        )

    controls = [f.to_dict() for f in run_control_probes()]
    yield ProbeEvent(
        "controls", f"{len(controls)} controls that need no model at all",
        {"controls": controls},
    )
    yield ProbeEvent(
        "declared",
        f"{len(DECLARED_PROBES)} probes declared but not executed - "
        "the apparatus to run them honestly does not exist here",
        {"declared": [
            {"probe_id": p.probe_id, "name": p.name, "surface": p.surface,
             "threat": p.threat, "control": p.control}
            for p in DECLARED_PROBES]},
    )
    yield ProbeEvent("sweep_done", "sweep finished", {})
