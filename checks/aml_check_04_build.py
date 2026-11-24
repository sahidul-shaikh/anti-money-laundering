"""Increment 4: the twelve phases, the evaluator, and the gates.

The graph and the gates are tested with a fake generator, so the blocking
behaviour is deterministic and costs nothing. The last section checks the
record of the real build, if one has been run.

Run: uv run python checks/aml_check_04_build.py
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from aml.build import bot, deliver, delivery_state
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

print("\ndelivery: provenance comes from the run, and only passing runs ship")


def _run(passed: bool, run_id: str = "development-20261124T101500Z") -> dict:
    tests = [{"passed": 19, "failed": 1}, {"passed": 20, "failed": 0}]
    return {
        "phase_id": "development", "run_id": run_id, "model": "haiku",
        "events": [{"kind": "tests", "data": t} for t in tests] + [{
            "kind": "done",
            "data": {"loop": {"passed": passed, "cost_usd": 0.0143, "attempts": [
                {"number": 2, "outcome": "pass", "produced": ["src/detector.py"],
                 "duration_s": 61.0, "cost_usd": 0.007}]}},
        }],
    }


lines = deliver.trailers(_run(True), "T-002").splitlines()
check("trailers carry task, stage, model and run ID",
      lines[:4] == ["Task: T-002", "Stage: development", "Model: haiku",
                    "Run-Id: development-20261124T101500Z"])
check("trailers carry each attempt's acceptance result",
      "Attempts: 2 (1: 19 passed 1 failed; 2: 20 passed)" in lines)
check("trailers carry the measured cost, labelled",
      "Cost-USD: 0.0143 (reported by Claude Code)" in lines)
check("the files shipped are the passing attempt's",
      deliver.final_files(_run(True)) == ["src/detector.py"])
for label, record in (("a failed run", _run(False)), ("a run with no run ID", _run(True, "")),
                      ("a passing run whose record is missing", _run(True))):
    try:
        deliver.check_deliverable(record)
        check(f"{label} is refused", False)
    except deliver.NotDeliverable as exc:
        check(f"{label} is refused", True, str(exc))
try:
    bot.token(Path(tempfile.mkdtemp()) / "absent")
    check("a missing bot token is refused", False)
except bot.NotTheBot:
    check("a missing bot token is refused", True)

fake = "ghp_FAKE0000000000000000000000000000000"
encoded = base64.b64encode(f"x-access-token:{fake}".encode()).decode()
try:
    deliver._git(["push", "origin", "refs/heads/no-such-branch-here"], deliver.ROOT, fake)
    check("a failed git command never shows the credential", False, "push unexpectedly worked")
except deliver.GitFailed as exc:
    check("a failed git command never shows the credential",
          fake not in str(exc) and encoded not in str(exc), str(exc)[:70])

print("\nwithholding the rules really withholds them")
# Phrases that state the semantics the withheld contract says it leaves out.
WITHHELD_FACTS = ["YYYY-MM-DD", "ISO-8601", "both inclusive", "Only credits",
                  "debits are ignored", "inclusive of both endpoints", "d+13",
                  "both window fields are None"]
code_phase = BY_ID["development"]
built = deliver.ROOT / deliver.BUILD_DIR
upstream = {d: (built / BY_ID[d].produces).read_text(encoding="utf-8")
            for d in code_phase.depends_on if (built / BY_ID[d].produces).exists()}
withheld_prompt = build_prompt(code_phase, upstream, withhold_rules=True)
leaked = [f for f in WITHHELD_FACTS if f in withheld_prompt]
check("a withheld code prompt states none of the withheld rules", not leaked,
      ", ".join(leaked) or f"{len(WITHHELD_FACTS)} phrases absent")
full_prompt = build_prompt(code_phase, upstream, withhold_rules=False)
check("the full-requirements prompt still states them",
      all(f in full_prompt for f in ("YYYY-MM-DD", "ISO-8601")))

print("\nthe delivery chain says what happened, including what it should not claim")


def _pr(state: str, reviews: tuple = (), checks: str = "SUCCESS") -> dict:
    return delivery_state.shape_pr({
        "number": 9, "title": "T-009: sample", "url": "https://example/pull/9",
        "author": {"login": "aml-factory-bot"}, "state": state,
        "createdAt": "2026-11-24T10:00:00Z", "mergedAt": "2026-11-24T11:00:00Z",
        "mergedBy": {"login": "owner"},
        "reviews": [{"state": r, "author": {"login": "owner"}, "submittedAt": "x"} for r in reviews],
        "statusCheckRollup": [{"name": "attack suite", "status": "COMPLETED" if checks != "RUNNING" else
                               "IN_PROGRESS", "conclusion": "" if checks == "RUNNING" else checks,
                               "startedAt": "2026-11-24T10:01:00Z"}],
        "commits": [{"oid": "abc1234def", "messageHeadline": "T-009: code",
                     "authors": [{"login": "aml-factory-bot"}],
                     "messageBody": "Task: T-009\nStage: development\nRun-Id: r1\n"
                                    "Attempts: 2 (1: 19 passed 1 failed; 2: 20 passed)\n"
                                    "Cost-USD: 0.0137 (reported by Claude Code)"}],
    })


task = {"id": "T-009", "intent_status": "accepted", "intent_author": "Owner",
        "plan_status": "accepted"}
states = lambda prs, **kw: {s["label"]: s["state"] for s in delivery_state.chain(task, prs, **kw)}  # noqa: E731
check("merged without an approving review is an override, never a tick",
      states([_pr("MERGED")])["Merged"] == "override"
      and states([_pr("MERGED")])["Human approval"] == "override")
check("merged with an approval is done",
      states([_pr("MERGED", ("APPROVED",))])["Merged"] == "done")
check("an open PR with green checks is waiting for a human",
      states([_pr("OPEN")])["Human approval"] == "waiting")
check("checks in progress show CI running, not waiting",
      states([_pr("OPEN", checks="RUNNING")])["CI"] == "running"
      and states([_pr("OPEN", checks="RUNNING")])["Human approval"] == "pending")
check("a failing check is shown as failed", states([_pr("OPEN", checks="FAILURE")])["CI"] == "failed")
check("a run ID without a run record is not a loop run",
      states([_pr("OPEN")])["Build loop"] == "manual"
      and states([_pr("OPEN")], recorded={"r1"})["Build loop"] == "done")
check("a live loop shows as running", states([], live={"attempt": 2})["Build loop"] == "running")

print("\na repeatable task starts a new cycle with each run, and takes only its own deliveries")
fresh_run = {"run_id": "r2", "passed": True, "attempts": "2 (1: 19 passed 1 failed; 2: 20 passed)",
             "cost": 0.015, "started_at": "2026-11-24T12:00:00Z"}
merged_before = [_pr("MERGED", ("APPROVED",))]
new_cycle = states(merged_before, cycle_start=fresh_run["started_at"], fresh=fresh_run)
check("a run newer than the last PR shows as this cycle's build loop",
      new_cycle["Build loop"] == "done")
check("the previous cycle's PR is not shown as this cycle's progress",
      new_cycle["Pull request"] == "pending" and new_cycle["Merged"] == "pending")
check("a refused run shows as failed, with nothing to deliver",
      states([], cycle_start="x", fresh={**fresh_run, "passed": False})["Build loop"] == "failed")
check("the newest run is older than the last PR: no new cycle",
      delivery_state.cycle([{"createdAt": "2026-11-24T13:00:00Z"}], None, fresh_run) == ("", None))
for task_id, accepted in (("T-001", False), ("T-006", True)):
    try:
        deliver.check_task(task_id)
        check(f"{task_id} {'accepts' if accepted else 'refuses'} factory deliveries", accepted)
    except deliver.NotDeliverable:
        check(f"{task_id} {'accepts' if accepted else 'refuses'} factory deliveries", not accepted)

print("\na delivery under way is shown step by step")
underway = {"task": "T-009", "started_at": "2026-11-24T12:05:00Z", "commit": "abc1234def", "error": ""}
shown = lambda step, **kw: states([], cycle_start="x", fresh=fresh_run,  # noqa: E731
                                  delivering={**underway, "step": step, **kw})
check("committing: Commit runs, Pull request waits",
      shown("commit")["Commit"] == "running" and shown("commit")["Pull request"] == "pending")
check("opening the PR: Commit done, Pull request runs",
      shown("pr")["Commit"] == "done" and shown("pr")["Pull request"] == "running")
check("a refused delivery shows on Commit, not silently",
      shown("refused", error="already delivered")["Commit"] == "failed")
check("once the PR exists, it wins over the delivery record",
      states([_pr("OPEN")], delivering={**underway, "step": "pr"})["Pull request"] == "done")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
