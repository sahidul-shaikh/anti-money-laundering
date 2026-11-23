"""Increment 3: contract, bands, mining and the gate.

Deliberately deterministic. The gate's job is to refuse things, so most of
this check feeds it fabricated evaluations and confirms it says no.

Run: uv run python checks/aml_check_03_improve.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from aml.corpus import build_corpus
from aml.improve import mining, tokenomics
from aml.improve.bands import (
    BAND_1,
    BAND_2,
    BAND_3,
    assess,
    band_for,
    detect,
    escalate,
    proportion_stderr,
)
from aml.improve.contract import (
    INVESTIGATOR_CONTRACT as CONTRACT,
    NoValueContract,
    ValueContract,
    require_contract,
)
from aml.improve.optimise import (
    ACCURACY,
    APPROVED,
    COST,
    INSUFFICIENT,
    REFUSED,
    Evaluation,
    Proposal,
    review,
    sign_test,
)
from aml.run.config import AgentConfig, case_count, system_prompt

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        failures.append(name)


def fake(kind: str, improved: int, regressed: int, cost_delta: float) -> Evaluation:
    """An evaluation with a known shape, to interrogate the gate."""
    before_correct = {f"a{i}": i >= improved for i in range(70)}
    after_correct = dict(before_correct)
    for i in range(improved):
        after_correct[f"a{i}"] = True
    for i in range(improved, improved + regressed):
        after_correct[f"a{i}"] = False
    base = {"accuracy": 0.74, "recall": 0.85, "specificity": 0.63,
            "cost_per_outcome_gbp": 17.79}
    return Evaluation(
        proposal=Proposal("X-01", kind, "explain_before_escalate", "", "", ""),
        before=base,
        after=base | {"cost_per_outcome_gbp": 17.79 + cost_delta},
        before_correct=before_correct,
        after_correct=after_correct,
    )


print("value contract")
try:
    require_contract(None)
    check("no contract, no build", False)
except NoValueContract:
    check("no contract, no build", True)
try:
    require_contract(ValueContract("x", 17, 12, 0.9, 0.85, (), "nobody"))
    check("no telemetry, no build", False)
except NoValueContract:
    check("no telemetry, no build", True)
check("a complete contract passes", require_contract(CONTRACT) is CONTRACT)
met = CONTRACT.realisation({"cost_per_outcome_gbp": 11.0, "recall": 0.95, "accuracy": 0.9})
check("realisation recognises all targets met", met["all_targets_met"])
missed = CONTRACT.realisation({"cost_per_outcome_gbp": 15.1, "recall": 0.86, "accuracy": 0.76})
check("and recognises when they are not", not missed["all_targets_met"],
      f"gap closed {missed['cost_gap_closed']:.0%}")

print("\nband arithmetic")
check("under one sigma is band 1", band_for(0.99) == BAND_1)
check("one to three sigma is band 2", band_for(1.0) == BAND_2 and band_for(2.99) == BAND_2)
check("three or more is band 3", band_for(3.0) == BAND_3)
se = proportion_stderr(0.743, 70)
d = detect("accuracy", 0.743, 0.85, se)
check("sigma is computed from the measurement's own dispersion",
      2.0 < d.sigma < 2.1, f"{d.sigma:.2f} sigma at se={se:.4f}")
check("a metric on target is band 1",
      detect("accuracy", 0.91, 0.85, se).band == BAND_1)
raised = escalate(d, "regulator asked", "Head of FCT")
check("a human can open band 3 deliberately",
      raised.band == BAND_3 and "Head of FCT" in raised.note)

print("\nmining clusters on what is observable")
corpus = build_corpus()
alert = next(a for a in corpus if len(a.transactions) == 1)
check("features come from the alert, not the label",
      "single_transaction" in mining.features(alert, 0))
check("siblings are a feature", "party_has_other_alerts" in mining.features(alert, 2))
subject = next(a for a in corpus if a.hero)
check("features are deterministic",
      mining.features(subject, 2) == mining.features(subject, 2))

fake_outcomes = [
    SimpleNamespace(alert_id=a.alert_id, correct=False, label=a.label,
                    handling_cost_gbp=17.0)
    for a in corpus[:2]
]
check("a cluster below the floor is not actionable",
      mining.mine(fake_outcomes, corpus) == [],
      f"floor is {mining.MATERIALITY_FLOOR}")

print("\nthe sign test")
check("no disagreements means no evidence", sign_test(0, 0) == 1.0)
check("three one-way flips are not significant", sign_test(3, 0) > 0.05)
check("six one-way flips are", sign_test(6, 0) < 0.05, f"p={sign_test(6, 0):.4f}")
check("a split result is not significant", sign_test(5, 4) > 0.05)
check("direction does not change the p value", sign_test(6, 0) == sign_test(0, 6))

print("\nthe gate refuses")
r = review(fake(ACCURACY, 3, 3, 0.0), "approver")
check("an accuracy change inside the noise is not approved",
      r.outcome == INSUFFICIENT, r.outcome)
r = review(fake(ACCURACY, 1, 9, 0.0), "approver")
check("an accuracy change that is significantly worse is refused",
      r.outcome == REFUSED, r.reason[:50])
r = review(fake(COST, 2, 12, -4.0), "approver")
check("a saving that measurably damages quality is refused",
      r.outcome == REFUSED, r.reason[:56])
r = review(fake(COST, 2, 4, -4.0), "approver")
check("a saving whose quality cost sits inside the noise needs more evidence",
      r.outcome == INSUFFICIENT, r.reason[:56])
r = review(fake(COST, 3, 3, +1.0), "approver")
check("a cost change that does not save is refused",
      r.outcome == REFUSED, r.reason[:40])
check("only an approval counts as approved",
      not review(fake(COST, 2, 4, -4.0), "x").approved)

print("\nthe gate approves")
r = review(fake(ACCURACY, 8, 0, -1.0), "approver")
check("a significant accuracy improvement", r.approved, r.reason[:52])
check("and records who approved it", r.approver == "approver")
r = review(fake(COST, 3, 3, -2.4), "approver")
check("a saving that leaves quality intact", r.approved, r.reason[:52])

print("\ncost mining names the traps")
premium = {"calls": 70, "tokens_in": 100_000, "cost_usd": 0.132, "accuracy": 0.743}
cheap = {"cost_usd": 0.070, "accuracy": 0.571}
spend = tokenomics.mine_spend(premium, cheap, corpus, system_tokens=800)
refused = [s for s in spend if s.verdict.startswith("REFUSE")]
check("the cheap-tier cascade is refused", any(s.cluster_id == "TOK-03" for s in refused))
check("the model outside the fleet is refused", any(s.cluster_id == "TOK-04" for s in refused))
check("only levers this system can pull become proposals",
      [p.proposal_id for p in tokenomics.cost_proposals(spend)] == ["CST-01"])

print("\nconsolidation arithmetic")
check("alerts resolve to fewer cases", case_count(corpus) < len(corpus),
      f"{len(corpus)} alerts -> {case_count(corpus)} cases")
base_prompt = system_prompt(AgentConfig())
check("every variant extends the base prompt rather than editing it",
      all(system_prompt(AgentConfig(**{f: True})).startswith(base_prompt)
          for f in ("explain_before_escalate", "evidence_for_close",
                    "consolidate_by_party")))

print("\nthe recorded run")
record = ARTIFACTS / "run_improve.json"
if record.exists():
    data = json.loads(record.read_text())
    noise = data["noise_floor"]
    check("a noise floor was measured",
          noise["improved"] + noise["regressed"] > 0,
          f"{noise['improved'] + noise['regressed']} of 70 alerts flipped on an "
          f"identical rerun")
    check("every decision records a tri-state outcome",
          all(d["outcome"] in {APPROVED, REFUSED, INSUFFICIENT}
              for d in data["decisions"]),
          ", ".join(f"{d['proposal_id']}={d['outcome']}" for d in data["decisions"]))
    check("the baseline is a consensus of repeated runs",
          data["before"].get("repeats", 0) > 1,
          f"{data['before'].get('repeats')} runs, "
          f"{data['before'].get('unstable_alerts')} alerts unstable across them")
    check("every decision names a reason",
          all(d["reason"] for d in data["decisions"]))
    any_approved = any(d["approved"] for d in data["decisions"])
    before_cost = data["before"]["cost_per_outcome_gbp"]
    after_cost = data["after"]["cost_per_outcome_gbp"]
    check("an approved change lowers cost; no approvals leaves it untouched",
          after_cost < before_cost if any_approved else after_cost == before_cost,
          f"GBP {before_cost:.2f} -> {after_cost:.2f}, "
          f"{'something approved' if any_approved else 'nothing approved'}")
else:
    check("run_improve.json exists", False, "run scripts/run_improve.py first")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
