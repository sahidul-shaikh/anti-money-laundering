"""Increment 1: routing, grading, telemetry.

Router mechanics are tested against a fake provider so failure and spend-cap
behaviour is deterministic. The last section makes real calls.

Run: uv run python checks/aml_check_01_run.py
"""

from __future__ import annotations

import sys

from aml.corpus import build_corpus
from aml.corpus.model import Alert, Party, Account, Transaction
from aml.core.ledger import Ledger, handling_cost_gbp
from aml.llm.bedrock import Completion, ProviderError
from aml.llm.fleet import load_fleet
from aml.llm.router import BudgetExceeded, NoEligibleModel, Router
from aml.run.engine import PROVIDER_ERROR, RunConfig, run_corpus
from aml.run.telemetry import layers
from aml.run.verdict import Unparseable, grade, parse

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        failures.append(name)


class FakeProvider:
    """Answers, or fails, exactly as the test asks."""

    def __init__(self, fail_models: set[str] | None = None, text: str = "{}") -> None:
        self.fail_models = fail_models or set()
        self.text = text
        self.seen: list[str] = []

    def complete(self, spec, system, prompt, max_tokens=2000, temperature=0.0):
        self.seen.append(spec.model)
        if spec.model in self.fail_models:
            raise ProviderError(f"{spec.model}: simulated outage")
        return Completion(
            text=self.text, model=spec.model, tokens_in=1000, tokens_out=200,
            tokens_cached=0, latency_ms=100, stop_reason="end_turn",
        )


FLEET = load_fleet()

print("routing policy")
ledger = Ledger()
router = Router(ledger, provider=FakeProvider(), fleet=FLEET)
check("cheapest eligible first",
      router.chain(0.0)[0].tier == "cheap",
      "->".join(m.tier for m in router.chain(0.0)))
check("quality floor excludes the cheap tier",
      [m.tier for m in router.chain(0.9)] == ["premium"])
check("rejected tier never routable",
      all(m.tier != "rejected" for m in router.chain(0.0)))
try:
    router.chain(1.5)
    check("impossible floor raises", False)
except NoEligibleModel:
    check("impossible floor raises", True)

print("\nfallback chain")
ledger = Ledger()
fake = FakeProvider(fail_models={"us.meta.llama3-3-70b-instruct-v1:0"})
router = Router(ledger, provider=fake, fleet=FLEET)
completion, spec = router.complete("A1", "sys", "prompt")
check("falls through to premium on provider error", spec.tier == "premium")
check("the failed attempt is recorded",
      ledger.failures() == 1 and len(ledger.calls) == 2,
      f"{len(ledger.calls)} calls, {ledger.failures()} failed")
check("failed attempt is not billed",
      next(c for c in ledger.calls if c.status == "error").cost_usd == 0.0)

print("\nspend cap")
ledger = Ledger()
router = Router(ledger, provider=FakeProvider(), fleet=FLEET, spend_cap_usd=0.002)
calls = 0
try:
    for n in range(50):
        router.complete(f"A{n}", "sys", "prompt")
        calls += 1
    check("spend cap stops the run", False, "never triggered")
except BudgetExceeded:
    check("spend cap stops the run", True, f"after {calls} calls, ${ledger.cost_usd:.4f}")

print("\ngrading")
alert = Alert(
    alert_id="T1", scenario="SAS10014", description="t", triggered="t", run_date="t",
    party=Party("1", "T", "INDIVIDUAL", "", "X", 1.0, "C", "S", "US"),
    account=Account("1", "P", "o", "ACTIVE", "USD", "R"),
    transactions=(Transaction("20181101", "111", 1.0, "DEBIT", "CASH", "US"),),
    label="escalate_to_case", provenance="real", hero=False, rationale="r",
)
verdict = parse('{"disposition":"escalate_to_case","risk_score":80,"narrative":"n",'
                '"evidence":[{"claim":"c","transaction_refs":["111","999"]}],'
                '"confidence":0.9}')
scored = grade(verdict, alert)
check("correct disposition detected", scored.correct)
check("invented citation caught", scored.invented == 1, f"{scored.cited} cited")
check("groundedness is the valid share", scored.groundedness == 0.5, str(scored.groundedness))
for bad in ("not json at all", '{"disposition":"maybe"}', "{broken"):
    try:
        parse(bad)
        check(f"rejects {bad[:18]!r}", False)
    except Unparseable:
        check(f"rejects {bad[:18]!r}", True)

print("\ninfrastructure failure is not agent failure")
ledger = Ledger()
dead = FakeProvider(fail_models={m.model for m in FLEET})
router = Router(ledger, provider=dead, fleet=FLEET)
_, dispositions = run_corpus(
    [alert_for_failure := build_corpus()[0]],
    RunConfig(workers=1), ledger=ledger, router=router,
)
recorded = ledger.outcomes[0].disposition
check("provider failure recorded as provider_error, not unparseable",
      recorded == PROVIDER_ERROR, recorded)
check("provider failure is not priced as a missed SAR",
      ledger.outcomes[0].handling_cost_gbp == 17.0,
      f"GBP {ledger.outcomes[0].handling_cost_gbp}")
check("telemetry reports provider errors separately",
      layers(ledger, dispositions)["SYSTEM"]["provider_errors"] == 1)

print("\nhandling cost")
check("escalation buys a human review",
      handling_cost_gbp("escalate_to_case", True, 0.0) == 17.0)
check("correct close is cheap",
      handling_cost_gbp("close_no_further_action", True, 0.0) == 0.2)
check("wrong close is the expensive one",
      handling_cost_gbp("close_no_further_action", False, 0.0) == 102.0)

print("\nlive slice")
corpus = build_corpus()
slice_ = [a for a in corpus if a.hero][:6]
ledger, dispositions = run_corpus(slice_, RunConfig(pin="cheap", workers=6))
check("every alert produced an outcome",
      len(ledger.outcomes) == len(slice_), f"{len(ledger.outcomes)}/{len(slice_)}")
check("no invented citations", ledger.invented_citations() == 0,
      f"{sum(o.cited for o in ledger.outcomes)} citations checked")
check("cost accrued", ledger.cost_usd > 0, f"${ledger.cost_usd:.5f}")

five = layers(ledger, dispositions)
check("five telemetry layers",
      list(five) == ["SYSTEM", "MODEL", "AGENT", "TRANSACTION", "VALUE"])
check("value layer prices against the manual baseline",
      five["VALUE"]["baseline_gbp_per_alert"] == 17.0,
      f"cost/outcome GBP {five['VALUE']['cost_per_outcome_gbp']}")
check("system layer saw the latency",
      five["SYSTEM"]["latency_p50_ms"] > 0,
      f"p50 {five['SYSTEM']['latency_p50_ms']}ms p95 {five['SYSTEM']['latency_p95_ms']}ms")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
