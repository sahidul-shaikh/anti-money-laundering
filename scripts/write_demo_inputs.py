"""Write the copy-paste inputs the console's chat panels expect.

A presenter should be able to open a text file, select all, and paste it into
the console. These are the exact alerts the recorded runs used, rendered the
same way the agent sees them.

Run: uv run python scripts/write_demo_inputs.py
"""

from __future__ import annotations

from pathlib import Path

from aml.corpus import build_corpus
from aml.corpus.render import render
from aml.security.injection import PAYLOADS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "demo"

# The alerts worth having to hand: the routing demo, the attack target, and one
# the agent over-escalates.
WANTED = {
    "11368": "cheap tier closed this one citing nothing; premium escalates it",
    "11366": "the attack target - must escalate, so a flip to close is clear harm",
    "11391": "an organisation, high-risk instruments",
    "S90001": "a large receipt that was retained - the agent over-escalates it",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = {a.alert_id: a for a in build_corpus()}

    for alert_id, note in WANTED.items():
        alert = corpus[alert_id]
        body = (
            f"# ALERT {alert.alert_id} | scenario {alert.scenario}\n"
            f"# {note}\n"
            f"# correct answer: {alert.label}\n"
            f"# paste everything below this line\n\n"
            f"{render(alert)}\n"
        )
        path = OUT / f"alert_{alert_id}.txt"
        path.write_text(body, encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}  ({len(body):,} chars)")

    payloads = ["# Injection payloads - paste one into the attacker field\n"]
    for p in PAYLOADS:
        payloads += [f"\n## {p.probe_id} {p.name}", f"# goal: {p.intent}", p.text]
    (OUT / "payloads.txt").write_text("\n".join(payloads) + "\n", encoding="utf-8")
    print(f"  {(OUT / 'payloads.txt').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
