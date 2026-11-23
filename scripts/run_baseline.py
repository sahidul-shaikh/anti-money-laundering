"""Run the whole corpus on each serving tier and record the baseline.

This is the Act 2 evidence: what the agent does before anything is improved.

Run: uv run python scripts/run_baseline.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from aml.corpus import build_corpus, summarise
from aml.core.ledger import Ledger
from aml.llm.fleet import load_fleet, serving
from aml.llm.router import Router
from aml.run.engine import RunConfig, run_corpus
from aml.run.telemetry import layers

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def main() -> None:
    corpus = build_corpus()
    print(f"corpus: {summarise(corpus)['total']} alerts "
          f"({summarise(corpus)['escalate']} escalate / {summarise(corpus)['close']} close)\n")

    runs = {}
    for spec in serving(load_fleet()):
        started = time.monotonic()
        ledger = Ledger()
        router = Router(ledger, spend_cap_usd=5.00, run_id=f"baseline-{spec.tier}")
        ledger, dispositions = run_corpus(
            corpus,
            RunConfig(pin=spec.tier, workers=8, label=f"baseline-{spec.tier}"),
            ledger=ledger,
            router=router,
        )
        elapsed = time.monotonic() - started
        five = layers(ledger, dispositions)
        runs[spec.tier] = {
            "model": spec.model,
            "elapsed_s": round(elapsed, 1),
            "summary": ledger.summary(),
            "telemetry": five,
            "outcomes": [o.__dict__ for o in ledger.outcomes],
            # What the agent actually wrote, so the console can show the
            # reasoning rather than only the score it earned.
            "verdicts": {
                d.alert.alert_id: {
                    "disposition": d.verdict.disposition if d.verdict else "",
                    "typology": d.verdict.typology if d.verdict else None,
                    "risk_score": d.verdict.risk_score if d.verdict else 0,
                    "confidence": d.verdict.confidence if d.verdict else 0.0,
                    "evidence": [dict(e) for e in d.verdict.evidence] if d.verdict else [],
                    "narrative": d.verdict.narrative if d.verdict else "",
                    "open_questions": list(d.verdict.open_questions) if d.verdict else [],
                    "regulatory_flags": list(d.verdict.regulatory_flags) if d.verdict else [],
                    "score_factors": [dict(f) for f in d.verdict.score_factors] if d.verdict else [],
                    "correct": d.grade.correct,
                    "groundedness": d.grade.groundedness,
                    "invented": d.grade.invented,
                    "notes": list(d.grade.notes),
                    "latency_ms": d.latency_ms,
                    "cost_usd": round(d.cost_usd, 6),
                    "error": d.error,
                }
                for d in dispositions
            },
        }
        print(f"{spec.tier:8s} {spec.model}")
        print(f"         {elapsed:5.1f}s  ${ledger.cost_usd:.4f}  "
              f"accuracy {ledger.accuracy():.1%}  recall {ledger.recall():.1%}  "
              f"specificity {ledger.specificity():.1%}")
        print(f"         groundedness {ledger.groundedness():.2f}  "
              f"invented {ledger.invented_citations()}  "
              f"unparseable {five['AGENT']['unparseable']}  "
              f"cost/outcome GBP {ledger.cost_per_outcome_gbp():.2f}\n")

    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / "run_baseline.json"
    path.write_text(json.dumps({"corpus": summarise(corpus), "runs": runs}, indent=2))

    print("=" * 72)
    print(f"{'':22s} {'cheap':>12s} {'premium':>12s}")
    for metric in ("accuracy", "recall", "specificity", "groundedness"):
        print(f"{metric:22s} "
              f"{runs['cheap']['summary'][metric]:>12.1%} "
              f"{runs['premium']['summary'][metric]:>12.1%}")
    for metric, fmt in (("cost_usd", "${:>11.4f}"), ("cost_per_outcome_gbp", "{:>12.2f}")):
        print(f"{metric:22s} "
              f"{fmt.format(runs['cheap']['summary'][metric]):>12s} "
              f"{fmt.format(runs['premium']['summary'][metric]):>12s}")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
