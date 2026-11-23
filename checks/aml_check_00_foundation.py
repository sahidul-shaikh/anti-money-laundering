"""Increment 0: the corpus loads, both classes exist, and Bedrock answers.

Run: uv run python checks/aml_check_00_foundation.py
"""

from __future__ import annotations

import collections
import json
import re
import sys

from aml.corpus import build_corpus, render, summarise, write_corpus
from aml.corpus.model import CLOSE, ESCALATE, REAL, SYNTHETIC
from aml.llm.bedrock import BedrockProvider, ProviderError
from aml.llm.fleet import load_fleet, serving

SYSTEM = """You are a Level-1 AML alert investigator for a US retail bank.
Review one transaction-monitoring alert and produce a disposition.

Respond with ONLY a single JSON object:
  disposition: close_no_further_action | escalate_to_case | insufficient_information
  evidence: [{claim, transaction_refs: [...]}]

Every transaction_ref you cite MUST appear in the supplied transaction list."""

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        failures.append(name)


print("corpus")
corpus = build_corpus()
summary = summarise(corpus)
check("70 alerts", summary["total"] == 70, str(summary["total"]))
check("35 real, 35 synthetic",
      summary["real"] == 35 and summary["synthetic"] == 35,
      f"{summary['real']}/{summary['synthetic']}")
check("both classes present",
      summary["escalate"] == 35 and summary["close"] == 35,
      f"escalate {summary['escalate']}, close {summary['close']}")
check("10 hero alerts", summary["hero"] == 10, str(summary["hero"]))
check("six scenarios", len(summary["scenarios"]) == 6, ",".join(summary["scenarios"]))

print("\nscenario code carries no signal")
by_scenario = collections.defaultdict(collections.Counter)
for alert in corpus:
    by_scenario[alert.scenario][alert.label] += 1
both = sum(1 for counts in by_scenario.values() if len(counts) == 2)
check("every scenario appears in both classes", both == 6, f"{both}/6")

print("\nhero set")
hero = [a for a in corpus if a.hero]
check("hero set spans both classes",
      {a.label for a in hero} == {ESCALATE, CLOSE},
      f"{sum(a.label == ESCALATE for a in hero)} escalate, {sum(a.label == CLOSE for a in hero)} close")
check("hero set spans both provenances",
      {a.provenance for a in hero} == {REAL, SYNTHETIC})

print("\nreferences")
for alert in corpus:
    if len(alert.refs) != len(alert.transactions):
        failures.append("refs unique within alert")
        break
check("references unique within every alert", "refs unique within alert" not in failures)
real_refs = {t.ref for a in corpus if a.provenance == REAL for t in a.transactions}
synth_refs = {t.ref for a in corpus if a.provenance == SYNTHETIC for t in a.transactions}
check("synthetic references cannot be mistaken for real",
      not (real_refs & synth_refs), f"{len(real_refs)} real, {len(synth_refs)} synthetic")

print("\nrendered view leaks nothing")
leaks = [
    a.alert_id for a in corpus
    if a.label in render(a) or (a.rationale and a.rationale[:40] in render(a))
]
check("no label or rationale in the prompt", not leaks, str(leaks[:3]))

print("\nfleet")
fleet = load_fleet()
routable = serving(fleet)
check("two serving tiers", len(routable) == 2, ",".join(m.tier for m in routable))
check("cheapest first", routable[0].tier == "cheap")
check("rejected tier is not routable",
      all(m.tier != "rejected" for m in routable))
premium = next(m for m in fleet if m.tier == "premium")
check("pricing arithmetic", round(premium.cost(1_000_000, 0), 4) == 0.5,
      f"${premium.cost(48_000, 16_000):.4f} for a 48k/16k pass")

print("\nbedrock, live")
provider = BedrockProvider()
subject = next(a for a in corpus if a.hero and a.provenance == REAL)
try:
    completion = provider.complete(routable[0], SYSTEM, render(subject), max_tokens=900)
    check("cheap tier answered", bool(completion.text),
          f"{completion.tokens_in} in / {completion.tokens_out} out, {completion.latency_ms}ms")
    match = re.search(r"\{.*\}", completion.text, re.S)
    parsed = json.loads(match.group(0)) if match else {}
    check("response parses as JSON", bool(parsed), parsed.get("disposition", ""))
    cited = [str(r) for e in parsed.get("evidence", []) for r in e.get("transaction_refs", [])]
    bad = [r for r in cited if r not in subject.refs]
    check("every citation is grounded", not bad, f"{len(cited)} cited, {len(bad)} invented")
    spec = routable[0]
    print(f"        cost ${spec.cost(completion.tokens_in, completion.tokens_out):.6f} "
          f"on {spec.model}")
except ProviderError as exc:
    check("cheap tier answered", False, str(exc)[:110])

path = write_corpus(corpus)
print(f"\nwrote {path.relative_to(path.parents[2])}")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
