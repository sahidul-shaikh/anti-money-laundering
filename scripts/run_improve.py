"""The improvement loop, start to finish.

Detect the deviation, mine the failures, propose with evidence, evaluate on
the same corpus, put every change to a gate, then measure the contract again.

Run: uv run python scripts/run_improve.py
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from aml.corpus import build_corpus
from aml.core.ledger import Ledger
from aml.improve import mining, optimise, tokenomics
from aml.improve.bands import assess
from aml.improve.contract import INVESTIGATOR_CONTRACT as CONTRACT
from aml.improve.contract import require_contract
from aml.run.config import AgentConfig, system_prompt
from aml.run.engine import RunConfig, run_corpus
from aml.llm.fleet import load_fleet

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
APPROVER = "Head of Financial Crime Technology"
# One run is not a measurement. Every comparison is the majority of this many.
REPEATS = 3


def main() -> None:
    require_contract(CONTRACT)
    corpus = build_corpus()
    baseline_file = json.loads((ARTIFACTS / "run_baseline.json").read_text())
    premium = baseline_file["runs"]["premium"]
    cheap = baseline_file["runs"]["cheap"]
    before = premium["summary"]
    outcomes = [SimpleNamespace(**o) for o in premium["outcomes"]]

    print(f"contract: {CONTRACT.name}")
    print(f"  baseline GBP {CONTRACT.baseline_gbp:.2f} -> target GBP "
          f"{CONTRACT.target_gbp:.2f}, recall >= {CONTRACT.target_recall:.0%}, "
          f"accuracy >= {CONTRACT.target_accuracy:.0%}\n")

    print("1. band detection")
    detections = assess(before, CONTRACT, outcomes)
    for d in detections:
        print(f"   {d.metric:22s} {d.observed:>8.3f} vs {d.target:<7} "
              f"{d.sigma:>5.2f} sigma  BAND {d.band}")
    worst = max(detections, key=lambda d: d.band)
    print(f"   -> {worst.action}\n")

    print("2. failure mining")
    failures = sum(1 for o in outcomes if not o.correct)
    clusters = mining.mine(outcomes, corpus)
    for c in clusters:
        print(f"   {c.signature:42s} n={c.count:<3} GBP {c.cost_gbp:>7.2f}  -> {c.proposal}")
    mined = mining.summarise(clusters, failures)
    print(f"   {mined['clustered']} of {failures} failures clustered, "
          f"{failures - mined['clustered']} below the materiality floor "
          f"of {mining.MATERIALITY_FLOOR}\n")

    print("3. cost mining")
    spec = next(m for m in load_fleet() if m.tier == "premium")
    system_tokens = tokenomics.measure_system_tokens(spec, system_prompt(AgentConfig()))
    spend = tokenomics.mine_spend(before, cheap["summary"], corpus, system_tokens)
    for s in spend:
        print(f"   {s.cluster_id} {s.name[:52]:54s} {s.verdict[:46]}")
    print()

    print("4. noise floor, then a consensus baseline")
    noise_ledger = Ledger()
    run_corpus(corpus, RunConfig(workers=8, agent=AgentConfig(), label="repeat"),
               ledger=noise_ledger)
    single_before = {o.alert_id: o.correct for o in outcomes}
    repeat_correct = {o.alert_id: o.correct for o in noise_ledger.outcomes}
    noise = optimise.Evaluation(
        proposal=optimise.Proposal("NOISE", "accuracy", "none", "", "", ""),
        before=before, after=noise_ledger.summary(),
        before_correct=single_before, after_correct=repeat_correct,
    )
    n_improved, n_regressed = noise.flips
    print(f"   {n_improved + n_regressed} of {len(corpus)} alerts answered "
          f"differently on an identical rerun ({n_improved} up, {n_regressed} down)")
    print(f"   accuracy moved {noise.delta('accuracy'):+.1%} with nothing changed, "
          f"p={noise.p_value:.3f}")
    print("   one run is not a measurement, so the baseline is re-measured as the "
          "majority of three")
    before_correct, before, base_spend = optimise.consensus(
        corpus, AgentConfig(), repeats=REPEATS, label="baseline"
    )
    print(f"   consensus baseline: accuracy {before['accuracy']:.1%}, "
          f"{before['unstable_alerts']} alerts unstable across {REPEATS} runs, "
          f"${base_spend:.4f}\n")

    print("5. proposals")
    proposals = optimise.propose(clusters) + tokenomics.cost_proposals(spend)
    for p in proposals:
        print(f"   {p.proposal_id} [{p.kind:8s}] {p.change}")
        print(f"            evidence: {p.evidence[:88]}")
    print()

    print("6. evaluation and gate")
    base = AgentConfig()
    evaluations, decisions, approved = [], [], base
    for proposal in proposals:
        evaluation = optimise.evaluate(
            proposal, corpus, before, base, before_correct, repeats=REPEATS
        )
        decision = optimise.review(evaluation, APPROVER)
        evaluations.append(evaluation)
        decisions.append(decision)
        verdict = {"approved": "APPROVED", "refused": "REFUSED ",
                   "insufficient_evidence": "NEED MORE"}[decision.outcome]
        improved, regressed = evaluation.flips
        print(f"   {verdict} {proposal.proposal_id}  "
              f"{improved} up / {regressed} down  p={evaluation.p_value:.3f}  "
              f"accuracy {evaluation.delta('accuracy'):+.1%}  "
              f"cost {evaluation.delta('cost_per_outcome_gbp'):+.2f}")
        print(f"            {decision.reason}")
        if decision.approved:
            approved = proposal.apply_to(approved)
    print()

    print(f"7. combined run with everything approved: {approved.changes or 'nothing'}")
    if approved.changes:
        _, after, _ = optimise.consensus(
            corpus, approved, repeats=REPEATS, label="improved"
        )
    else:
        # Nothing cleared the gate, so the estate is unchanged. Re-running it
        # would only show the noise again.
        after = before
    for metric in ("accuracy", "recall", "specificity", "groundedness"):
        print(f"   {metric:16s} {before[metric]:>7.1%} -> {after[metric]:>7.1%}")
    print(f"   {'cost/outcome':16s} {before['cost_per_outcome_gbp']:>7.2f} -> "
          f"{after['cost_per_outcome_gbp']:>7.2f}  GBP")
    print()

    realisation = CONTRACT.realisation(after)
    print("8. contract")
    print("   decisions: " + ", ".join(f"{d.proposal_id}={d.outcome}" for d in decisions))
    for key in ("cost_target_met", "recall_target_met", "accuracy_target_met"):
        print(f"   {key:22s} {realisation[key]}")
    print(f"   cost gap closed        {realisation['cost_gap_closed']:.0%}")
    print(f"   all targets met        {realisation['all_targets_met']}")

    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / "run_improve.json"
    path.write_text(json.dumps({
        "contract": CONTRACT.__dict__ | {"telemetry": list(CONTRACT.telemetry)},
        "detections": [d.to_dict() for d in detections],
        "clusters": [c.to_dict() for c in clusters],
        "mining_summary": mined,
        "spend_clusters": [s.to_dict() for s in spend],
        "system_tokens": system_tokens,
        "proposals": [p.to_dict() for p in proposals],
        "noise_floor": noise.to_dict(),
        "evaluations": [e.to_dict() for e in evaluations],
        "decisions": [d.to_dict() for d in decisions],
        "approved_changes": approved.changes,
        "before": before,
        "after": after,
        "realisation": realisation,
    }, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
