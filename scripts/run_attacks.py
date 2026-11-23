"""Fire the swarm at the agent with the guardrail off, then on.

This is the Act 3 evidence. The same payloads, the same alert, the same model
- the only difference is where the attacker's text sits in the prompt.

Run: uv run python scripts/run_attacks.py
"""

from __future__ import annotations

import json
from pathlib import Path

from aml.corpus import build_corpus
from aml.core.ledger import Ledger
from aml.llm.router import Router
from aml.security.swarm import (
    DECLARED_PROBES,
    EXECUTED,
    Finding,
    run_control_probes,
    run_injection_probes,
    summarise,
)

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
TARGET = "11366"   # structured withdrawals, 8 transactions


def main() -> None:
    corpus = build_corpus()
    alert = next(a for a in corpus if a.alert_id == TARGET)
    print(f"target: alert {alert.alert_id}  {alert.party.name}  "
          f"{alert.description}  ({len(alert.transactions)} transactions)")
    print(f"ground truth: {alert.label}\n")

    ledger = Ledger()
    router = Router(ledger, spend_cap_usd=2.00, run_id="attacks")

    results = {}
    for tier in ("cheap", "premium"):
        for guardrail in (False, True):
            state = "on" if guardrail else "off"
            findings = run_injection_probes(
                alert, router, guardrail=guardrail, pin=tier
            )
            results[f"{tier}:{state}"] = findings
            print(f"{tier:8s} guardrail {state.upper():3s}")
            for f in findings:
                flag = ("EXPLOITED" if f.confirmed
                        else "discarded" if f.outcome == "exploited"
                        else "defended ")
                print(f"   {flag} {f.probe_id} {f.name:30s} {f.observation[:56]}")
            print(f"   -> {summarise(findings)['confirmed']} of {len(findings)} "
                  f"confirmed exploited\n")

    controls = run_control_probes()
    declared = [
        Finding(p.probe_id, p.name, p.mode, "not-run", p.threat, p.control)
        for p in DECLARED_PROBES
    ]
    print("controls (no model involved)")
    for f in controls:
        print(f"   defended  {f.probe_id} {f.name:38s} {f.observation[:52]}")
    print("\ndeclared, not executed")
    for f in declared:
        print(f"   not-run   {f.probe_id} {f.name}")

    everything = results["premium:on"] + controls + declared
    overall = summarise(everything)

    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / "run_attacks.json"
    path.write_text(json.dumps({
        "target": {
            "alert_id": alert.alert_id,
            "party": alert.party.name,
            "label": alert.label,
            "transactions": len(alert.transactions),
        },
        "by_tier_and_guardrail": {
            key: [f.to_dict() for f in value] for key, value in results.items()
        },
        "controls": [f.to_dict() for f in controls],
        "declared": [f.to_dict() for f in declared],
        "summary_with_guardrail": overall,
        "cost_usd": round(ledger.cost_usd, 6),
        "calls": len(ledger.calls),
    }, indent=2))

    print("\n" + "=" * 68)
    print(f"{'confirmed':10s} {'guardrail off':>16s} {'guardrail on':>16s}")
    for tier in ("cheap", "premium"):
        print(f"{tier:10s} "
              f"{summarise(results[f'{tier}:off'])['confirmed']:>14d}/5 "
              f"{summarise(results[f'{tier}:on'])['confirmed']:>14d}/5")
    discarded = sum(summarise(v)["discarded_on_rerun"] for v in results.values())
    print(f"discarded as unreproducible  {discarded}")
    print(f"posture with the guardrail   {overall['defended']} defended, "
          f"{overall['confirmed']} confirmed exploited, {overall['declared']} declared")
    print(f"{len(ledger.calls)} calls, ${ledger.cost_usd:.4f}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
