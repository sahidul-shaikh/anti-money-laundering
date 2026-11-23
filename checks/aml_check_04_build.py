"""Increment 4: the twelve phases, the evaluator, and the gates.

The graph and the gates are tested with a fake generator, so the blocking
behaviour is deterministic and costs nothing. The last section checks the
record of the real build, if one has been run.

Run: uv run python checks/aml_check_04_build.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from aml.build.claude_code import Generation
from aml.build.evaluator import MIN_LENGTH, evaluate
from aml.build.library import Library
from aml.build.orchestrator import GateBlocked, build, build_prompt
from aml.build.phases import BY_ID, GATES, PHASES, order

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
FILLER = "x" * MIN_LENGTH
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        failures.append(name)


def generator(drop: str | None = None, short: bool = False):
    """Produces exactly what the brief asked for, minus anything dropped."""

    def gen(prompt: str) -> Generation:
        sections = re.search(r"in capitals: (.+?)\.\n", prompt)
        markers = sections.group(1).split(", ") if sections else []
        ids = re.search(r"identifiers in the text: (.+?)\.\n", prompt)
        tokens = ids.group(1).split(", ") if ids else []
        if drop:
            markers = [m for m in markers if drop.upper() not in m.upper()]
            tokens = [t for t in tokens if drop.upper() not in t.upper()]
        body = "\n".join(f"## {m}\ncontent" for m in markers) + "\n" + " ".join(tokens)
        return Generation(
            text=body if short else body + "\n" + FILLER,
            cost_usd=0.1, duration_ms=100, turns=1, session_id="t", model="fake",
        )

    return gen


def sandbox():
    tmp = Path(tempfile.mkdtemp())
    return tmp, Library(root=tmp / "lib")


print("the graph")
check("twelve phases", len(PHASES) == 12, str(len(PHASES)))
sequence = order()
seen: set[str] = set()
valid = True
for phase in sequence:
    if not set(phase.depends_on) <= seen:
        valid = False
    seen.add(phase.phase_id)
check("dependencies resolve to a topological order", valid,
      " -> ".join(p.phase_id for p in sequence[:5]) + " ...")
check("four phases are gated", len(GATES) == 4, ", ".join(GATES))
check("the threat model is written before any implementation",
      sequence.index(BY_ID["spec"]) < sequence.index(BY_ID["development"]),
      f"spec at {sequence.index(BY_ID['spec']) + 1}, "
      f"development at {sequence.index(BY_ID['development']) + 1}")
# A document phase is checked on its headings; a code phase has no headings to
# check and names an acceptance suite instead. Either way something outside the
# phase decides whether it passed.
check("every phase names what will judge it",
      all(p.markers or p.verify_with for p in PHASES),
      ", ".join(f"{p.phase_id}:{'markers' if p.markers else 'suite'}"
                for p in PHASES if p.kind == "code"))

print("\nthe brief carries its dependencies")
prompt = build_prompt(BY_ID["spec"], {"contract": "BASELINE GBP 17.00 per alert"})
check("upstream artifacts are in the prompt", "BASELINE GBP 17.00" in prompt)
check("the required sections are named", "THREAT MODEL" in prompt)
check("the required identifiers are named", "AC-1" in prompt and "T-1" in prompt)

print("\nthe evaluator")
spec = BY_ID["spec"]
good = "## ACCEPTANCE CRITERIA\nAC-1 body\n## THREAT MODEL\nT-1 body\n" + FILLER
check("a complete artifact passes", evaluate(spec, good).passed)
missing = evaluate(spec, good.replace("## THREAT MODEL", "## OTHER")).missing
check("a missing section is named", "THREAT MODEL" in missing, ", ".join(missing))
mention = ("## SCOPE\nA threat model will be produced in a later phase.\n"
           "## ACCEPTANCE CRITERIA\nAC-1 and T-1 apply.\n" + FILLER)
check("a passing mention is not a section", not evaluate(spec, mention).passed,
      "the phrase appears in prose but there is no such heading")
stub = "## ACCEPTANCE CRITERIA\n## THREAT MODEL\nAC-1 T-1"
check("a stub does not pass", not evaluate(spec, stub).passed,
      f"minimum {MIN_LENGTH} characters")

print("\nthe build blocks")
for label, gen in (
    ("the threat model is deleted from the spec", generator(drop="THREAT MODEL")),
    ("an acceptance criterion is missing", generator(drop="AC-1")),
    ("the artifact is too short to review", generator(short=True)),
):
    tmp, lib = sandbox()
    try:
        build("t", workspace=tmp / "ws", library=lib, generator=gen)
        check(f"blocked when {label}", False)
    except GateBlocked as exc:
        check(f"blocked when {label}", True, str(exc)[:56])
    shutil.rmtree(tmp, ignore_errors=True)

tmp, lib = sandbox()
try:
    build("t", workspace=tmp / "ws", library=lib, generator=generator(),
          approver=lambda p, e, a: "")
    check("blocked when a human refuses the gate", False)
except GateBlocked as exc:
    check("blocked when a human refuses the gate", True, str(exc)[:56])
shutil.rmtree(tmp, ignore_errors=True)

print("\nnothing downstream runs after a block")
tmp, lib = sandbox()
try:
    build("t", workspace=tmp / "ws", library=lib, generator=generator(drop="THREAT MODEL"))
except GateBlocked:
    pass
# A build that stops early records itself as partial, so it can never be
# mistaken for, or overwrite, a full twelve-phase run.
partial = tmp / "ws" / "t" / "build.partial.json"
check("a blocked build is recorded as partial", partial.exists(),
      "build.partial.json, not build.json")
record = json.loads(partial.read_text())
check("the build stops at the failing phase", len(record["results"]) == 2,
      f"{len(record['results'])} phases attempted of 12")
check("the failure is recorded, not swallowed",
      not record["results"][-1]["evaluation"]["passed"])
shutil.rmtree(tmp, ignore_errors=True)

print("\nthe library compounds")
tmp, lib = sandbox()
first = build("product-a", workspace=tmp / "ws", library=lib, generator=generator())
second = build("product-b", workspace=tmp / "ws", library=lib, generator=generator())
check("the first build creates every asset",
      first["library"]["inherited"] == 0 and first["library"]["created"] > 0,
      f"{first['library']['created']} created")
check("the second inherits them",
      second["library"]["created"] == 0
      and second["library"]["inherited"] == first["library"]["created"],
      f"reuse {second['library']['reuse_rate']:.0%}")
check("assets persist on disk",
      second["library"]["on_disk"] == first["library"]["created"])
shutil.rmtree(tmp, ignore_errors=True)

print("\nthe real build")
record_path = ARTIFACTS / "builds" / "aml-alert-investigator" / "build.json"
if record_path.exists():
    real = json.loads(record_path.read_text())
    check("phases passed", real["phases_passed"] == real["phases_total"],
          f"{real['phases_passed']} of {real['phases_total']}")
    check("every artifact was evaluated",
          all(r["evaluation"]["length"] > 0 for r in real["results"]))
    check("gated phases name an approver",
          all(r["approved_by"] for r in real["results"]
              if r["gated"] and r["evaluation"]["passed"]))
    check("the build cost was recorded", real["cost_usd"] > 0,
          f"${real['cost_usd']:.4f}")
    produced = list(record_path.parent.glob("*.md"))
    check("artifacts are on disk", len(produced) == real["phases_passed"],
          f"{sum(p.stat().st_size for p in produced) // 1024} KB across "
          f"{len(produced)} documents")

    print("\n  the real artifacts still satisfy the stricter evaluator")
    regraded = {
        p.phase_id: evaluate(p, (record_path.parent / p.produces).read_text(encoding="utf-8"))
        for p in PHASES if (record_path.parent / p.produces).exists()
    }
    check("every generated artifact passes on re-evaluation",
          all(e.passed for e in regraded.values()),
          ", ".join(k for k, e in regraded.items() if not e.passed) or "all 12")
else:
    print("  SKIP  no real build yet: run scripts/run_build.py")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
