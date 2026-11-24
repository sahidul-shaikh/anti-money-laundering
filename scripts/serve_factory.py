"""Serve the console and run build phases live on request.

Standard library only. Serving the console from here rather than opening the
file directly makes the page same-origin with the API, so the browser will
talk to it without any cross-origin arrangement.

Run: uv run python scripts/serve_factory.py
Then open http://localhost:8765
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from aml.build import brief as brief_module
from aml.build import delivery_state
from aml.build.bot import NotTheBot
from aml.build.claude_code import BuildToolError, generate
from aml.build.deliver import GitFailed, NotDeliverable
from aml.build.deliver import deliver as deliver_run
from aml.build.code import run_tests
from aml.build.live import (
    LiveError,
    LiveEvent,
    reevaluate,
    run_code_phase_live,
    run_phase_live,
)
from aml.build.orchestrator import build_prompt
from aml.build.phases import BY_ID, PHASES, order
from aml.core.ledger import Ledger
from aml.corpus import build_corpus
from aml.llm.fleet import CACHE_READ_RATE, load_fleet
from aml.llm.router import Router
from aml.run import rules as rules_module
from aml.run.chat import ask as chat_ask
from aml.corpus.render import render as render_alert
from aml.run.chat import route as chat_route
from aml.run.chat import attack as chat_attack
from aml.run.config import (EXPLAIN_BEFORE_ESCALATE, AgentConfig,
                            system_prompt as agent_system_prompt)
from aml.run.engine import RunConfig, run_alert
from aml.run.routing import RoutingPolicy, break_tier, route_alert
from aml.security.envelope import CLOSE, GUARDRAIL, OPEN, PREAMBLE
from aml.security.injection import PAYLOADS
from aml.security.tools import UNGRANTABLE, investigator_registry
from aml.security.paired import paired_probe, sweep
from aml.improve.live import ab_live
from aml.improve.optimise import Proposal
from aml.improve.tokenomics import measure_system_tokens
from aml.run.prompts import SYSTEM_PROMPT, user_turn
from aml.security.swarm import DECLARED_PROBES, run_control_probes

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PRODUCT = "aml-alert-investigator"
BUILD_DIR = ARTIFACTS / "builds" / PRODUCT
LIVE_DIR = ARTIFACTS / "live"
UI_DIR = ROOT / "scripts" / "ui"
SKILLS_DIR = ROOT / "library" / "aml" / "skills"
ORACLE = ROOT / "checks" / "acceptance" / "test_detector_contract.py"
PILLARS = ROOT / "library" / "pillars.json"
BASELINE = ARTIFACTS / "run_baseline.json"
IMPROVE = ARTIFACTS / "run_improve.json"
ATTACKS = ARTIFACTS / "run_attacks.json"
DEMO_DIR = ARTIFACTS / "demo"
PORT = 8765

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


@dataclass
class Run:
    """One live phase run, and the queues watching it."""

    phase_id: str
    run_id: str = ""
    events: list[dict] = field(default_factory=list)
    listeners: list[queue.Queue] = field(default_factory=list)
    finished: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def publish(self, event: LiveEvent) -> None:
        payload = event.to_dict()
        with self.lock:
            self.events.append(payload)
            listeners = list(self.listeners)
        for listener in listeners:
            listener.put(payload)

    def close(self) -> None:
        self.finished = True
        with self.lock:
            listeners = list(self.listeners)
        for listener in listeners:
            listener.put(None)


RUNS: dict[str, Run] = {}
RUN_LOCK = threading.Lock()

# The delivery under way, or the last one refused: task, run_id, step, commit,
# error, started_at. Read by the rail; cleared when a delivery succeeds or a
# new implementation run starts.
DELIVERY: dict = {}
DELIVERY_FAILURES = (NotDeliverable, NotTheBot, GitFailed, subprocess.CalledProcessError)


def auto_task() -> str | None:
    """The task a passing run is delivered to without asking: the only one that accepts them."""
    takers = [t["id"] for t in delivery_state.read_tasks()
              if t["deliverable"] and t["intent_status"] == "accepted"]
    return takers[0] if len(takers) == 1 else None


def deliver_tracked(task: str):
    """Deliver, recording each step as it happens so the rail can show it."""
    DELIVERY.clear()
    DELIVERY.update(task=task, step="commit", commit="", error="",
                    started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    try:
        done = deliver_run(task, on_step=lambda step, **detail: DELIVERY.update(step=step, **detail))
    except DELIVERY_FAILURES as exc:
        reason = str(exc) if not isinstance(exc, subprocess.CalledProcessError) \
            else "opening the pull request failed"
        DELIVERY.update(step="refused", error=reason)
        raise
    DELIVERY.clear()
    delivery_state._cache["at"] = 0.0
    return done


def passed(run: Run) -> bool:
    done = next((e for e in run.events if e["kind"] == "done"), None)
    return bool(done and done.get("data", {}).get("loop", {}).get("passed"))

ROUTE_RUNS: dict[str, Run] = {}
PROBE_RUNS: dict[str, Run] = {}
IMPROVE_RUNS: dict[str, Run] = {}
CORPUS: list = []


def corpus() -> list:
    """The seventy alerts, loaded once and kept."""
    if not CORPUS:
        CORPUS.extend(build_corpus())
    return CORPUS


def open_in_editor(path: Path) -> bool:
    """Bring the artifact up in VS Code, if the editor is on PATH."""
    try:
        subprocess.Popen(
            ["code", "-r", str(path)],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError:
        return False


def upstream_for(phase_id: str) -> dict[str, str]:
    """Whatever the phases this one depends on produced, live or recorded."""
    phase = BY_ID[phase_id]
    upstream = {}
    for dependency in phase.depends_on:
        path = BUILD_DIR / BY_ID[dependency].produces
        upstream[dependency] = (
            path.read_text(encoding="utf-8") if path.exists() else ""
        )
    return upstream


def live_build() -> dict | None:
    """The implementation loop if it is running now, for the delivery rail.

    The start time is read off the run ID, which was minted when the run began.
    """
    run = RUNS.get("development")
    if not run or run.finished:
        return None
    attempts = sum(e["kind"] == "attempt" for e in run.events)
    return {"run_id": run.run_id, "attempt": max(attempts, 1), "max_attempts": 3,
            "started_at": delivery_state.started_at(run.run_id)}


def start_run(
    phase_id: str, focus: bool, model: str = "sonnet",
    withhold_rules: bool = False,
) -> Run:
    phase = BY_ID[phase_id]
    artifact = BUILD_DIR / phase.produces
    LIVE_DIR.mkdir(parents=True, exist_ok=True)

    run_id = f"{phase_id}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    run = Run(phase_id=phase_id, run_id=run_id)
    with RUN_LOCK:
        RUNS[phase_id] = run
    if phase.kind == "code":
        DELIVERY.clear()

    if focus:
        open_in_editor(artifact)

    def worker() -> None:
        try:
            prompt = build_prompt(
                phase, upstream_for(phase_id), brief_module.load(),
                withhold_rules=withhold_rules,
            )
            events = (
                run_code_phase_live(
                    phase, prompt, BUILD_DIR,
                    LIVE_DIR / f"{phase_id}.events.jsonl", model=model,
                )
                if phase.kind == "code"
                else run_phase_live(
                    phase, prompt, artifact,
                    LIVE_DIR / f"{phase_id}.events.jsonl", model=model,
                )
            )
            for event in events:
                run.publish(event)
        except LiveError as exc:
            run.publish(LiveEvent("error", 0.0, str(exc)))
        finally:
            run.close()
            save_run_summary(run, model=model, withheld=withhold_rules)
        # A passing implementation run goes straight to a pull request: the
        # factory acts up to the merge gate on its own, and stops there.
        task = auto_task() if phase.kind == "code" and passed(run) else None
        if task:
            try:
                deliver_tracked(task)
            except DELIVERY_FAILURES:
                pass  # recorded in DELIVERY and shown on the rail as refused

    threading.Thread(target=worker, daemon=True).start()
    return run



def alert_catalogue() -> list[dict]:
    """Every alert, with what the recorded baseline did with it."""
    recorded = {}
    if BASELINE.exists():
        book = json.loads(BASELINE.read_text(encoding="utf-8"))["runs"]
        for tier, run in book.items():
            for outcome in run["outcomes"]:
                recorded.setdefault(outcome["alert_id"], {})[tier] = {
                    "disposition": outcome["disposition"],
                    "correct": outcome["correct"],
                    "cited": outcome["cited"],
                    "confidence": outcome["confidence"],
                }

    catalogue = []
    for alert in corpus():
        seen = recorded.get(alert.alert_id, {})
        cheap, premium = seen.get("cheap"), seen.get("premium")
        catalogue.append({
            "alert_id": alert.alert_id,
            "party": alert.party.name,
            "scenario": alert.scenario,
            "description": alert.description,
            "label": alert.label,
            "provenance": alert.provenance,
            "transactions": len(alert.transactions),
            "refs": len(alert.refs),
            "recorded": seen,
            # The alerts worth demonstrating: cheap answered with nothing to
            # point at and got it wrong, premium got it right.
            "candidate": bool(
                cheap and premium and not cheap["correct"] and premium["correct"]
                and cheap["cited"] == 0
                and cheap["disposition"] != "provider_error"
            ),
        })
    return catalogue


def recorded_runs() -> dict:
    """The measured baseline: summaries, five-layer telemetry, spend clusters."""
    payload = {"found": BASELINE.exists()}
    if BASELINE.exists():
        book = json.loads(BASELINE.read_text(encoding="utf-8"))
        payload["corpus"] = book["corpus"]
        payload["runs"] = {
            tier: {
                "model": run["model"],
                "elapsed_s": run["elapsed_s"],
                "summary": run["summary"],
                "telemetry": run["telemetry"],
            }
            for tier, run in book["runs"].items()
        }
        payload["policy"] = routing_counterfactual(book)
    if IMPROVE.exists():
        improve = json.loads(IMPROVE.read_text(encoding="utf-8"))
        payload["spend_clusters"] = improve.get("spend_clusters", [])
        payload["system_tokens"] = improve.get("system_tokens")
        payload["contract"] = improve.get("contract")
    payload["fleet"] = [
        {"tier": m.tier, "model": m.model, "quality": m.quality,
         "quality_basis": m.quality_basis, "price_in": m.price_in,
         "price_out": m.price_out, "serving": m.serving}
        for m in load_fleet()
    ]
    return payload


def routing_counterfactual(book: dict) -> dict:
    """What the evidence-gated policy would have scored on the recorded runs.

    Both tiers answered every alert, so this is arithmetic on measured data,
    not a simulation - but it is not the same as having run the policy, and
    the console says so.
    """
    cheap = {o["alert_id"]: o for o in book["runs"]["cheap"]["outcomes"]}
    premium = {o["alert_id"]: o for o in book["runs"]["premium"]["outcomes"]}
    ids = [
        a for a in sorted(set(cheap) & set(premium))
        if cheap[a]["disposition"] != "provider_error"
        and premium[a]["disposition"] != "provider_error"
    ]

    def score(label, pick, spend):
        final = {a: pick(a) for a in ids}
        positives = [a for a in ids if final[a]["label"] == "escalate_to_case"]
        return {
            "label": label,
            "premium_calls": sum(1 for a in ids if final[a] is premium[a]),
            "accuracy": round(sum(1 for a in ids if final[a]["correct"]) / len(ids), 4),
            "recall": round(
                sum(1 for a in positives if final[a]["correct"]) / len(positives), 4),
            "cost_usd": round(spend(final), 6),
            "handling_gbp": round(
                sum(final[a]["handling_cost_gbp"] for a in ids) / len(ids), 2),
        }

    gated = lambda a: premium[a] if cheap[a]["cited"] == 0 else cheap[a]  # noqa: E731
    return {
        "alerts": len(ids),
        "excluded_provider_errors": len(set(cheap) | set(premium)) - len(ids),
        "policies": [
            score("all cheap", lambda a: cheap[a],
                  lambda f: sum(cheap[a]["cost_usd"] for a in ids)),
            score("all premium", lambda a: premium[a],
                  lambda f: sum(premium[a]["cost_usd"] for a in ids)),
            score("evidence-gated", gated,
                  lambda f: sum(cheap[a]["cost_usd"] for a in ids)
                  + sum(premium[a]["cost_usd"] for a in ids if f[a] is premium[a])),
        ],
    }



def secures_recorded() -> dict:
    """The recorded sweep, the controls, and the threat model the factory wrote."""
    payload = {
        "payloads": [
            {"probe_id": p.probe_id, "name": p.name, "intent": p.intent, "text": p.text}
            for p in PAYLOADS
        ],
        "declared": [
            {"probe_id": p.probe_id, "name": p.name, "surface": p.surface,
             "threat": p.threat, "control": p.control}
            for p in DECLARED_PROBES
        ],
        "controls": [f.to_dict() for f in run_control_probes()],
        "envelope": {
            "name": GUARDRAIL,
            "preamble": PREAMBLE,
            "open": OPEN,
            "close": CLOSE,
        },
        "scopes": {
            "granted": sorted(investigator_registry().granted),
            "ungrantable": sorted(UNGRANTABLE),
        },
        "found": ATTACKS.exists(),
    }
    if ATTACKS.exists():
        payload["sweep"] = json.loads(ATTACKS.read_text(encoding="utf-8"))

    # The threat model is a factory artifact, so it is quoted rather than retyped.
    spec = BUILD_DIR / "spec.md"
    if spec.exists():
        body = spec.read_text(encoding="utf-8")
        # The stage numbers its own headings, and a re-run can renumber them,
        # so match on the words rather than on the format.
        match = re.search(
            r"^#{1,6}[^\n]*THREAT MODEL[^\n]*$(.*?)(?=^#{1,6}[ \t]|\Z)",
            body, re.M | re.S | re.I,
        )
        payload["threat_model"] = {
            "source": "artifacts/builds/aml-alert-investigator/spec.md",
            "section": (match.group(0).strip() if match else ""),
            "threat_ids": sorted(set(re.findall(r"\bT-\d+\b", body))),
        }
    skill = SKILLS_DIR / "threat-modelling.md"
    if skill.exists():
        payload["skill"] = {
            "name": "threat-modelling",
            "file": "library/aml/skills/threat-modelling.md",
            "body": skill.read_text(encoding="utf-8"),
        }
    return payload



def improve_recorded() -> dict:
    """The recorded evaluation: clusters, proposals, gate decisions, bands."""
    if not IMPROVE.exists():
        return {"found": False}
    d = json.loads(IMPROVE.read_text(encoding="utf-8"))
    d["found"] = True
    return d




# The two edits the Evaluation panel can make to prove the evaluators are real.
# Both are exact string swaps with a known inverse, so nothing can be left
# half-broken: whatever the panel breaks, it can always put back.
TAMPERS = {
    "document": {
        "file": "spec.md",
        "whole": "## 5. THREAT MODEL",
        "broken": "## 5. Security notes",
        "phase": "spec",
        "what": "renames the THREAT MODEL heading",
    },
    "code": {
        "file": "src/detector.py",
        "whole": "upper_bound: float = 9999.99",
        "broken": "upper_bound: float = 9000.0",
        "phase": "development",
        "what": "moves the upper bound of the structuring band",
    },
}


def tamper_state(name: str) -> dict:
    spec = TAMPERS[name]
    path = BUILD_DIR / spec["file"]
    body = path.read_text(encoding="utf-8") if path.exists() else ""
    # The heading carries a section number the stage chooses, so match on the
    # words rather than on the exact string the catalogue was built with.
    intact = spec["whole"] in body
    broken = spec["broken"] in body
    if name == "document" and not (intact or broken):
        match = re.search(r"^#{1,6}[^\n]*THREAT MODEL[^\n]*$", body, re.M)
        if match:
            spec = dict(spec, whole=match.group(0))
            intact = True
    return {"name": name, "file": spec["file"], "phase": spec["phase"],
            "what": spec["what"], "intact": intact, "broken": broken,
            "whole": spec["whole"], "broken_text": spec["broken"]}


def apply_tamper(name: str, action: str) -> dict:
    state = tamper_state(name)
    path = BUILD_DIR / state["file"]
    body = path.read_text(encoding="utf-8")
    if action == "break" and state["intact"]:
        body = body.replace(state["whole"], state["broken_text"], 1)
    elif action == "restore" and state["broken"]:
        body = body.replace(state["broken_text"], state["whole"], 1)
    else:
        return {**state, "changed": False}
    path.write_text(body, encoding="utf-8")
    return {**tamper_state(name), "changed": True, "action": action}


def single_case(alert_id: str, change: str) -> dict:
    """One alert, before and after a configuration change, with both answers.

    The paired evaluation over seventy alerts is the measurement that decides
    whether a change ships. This is the one case a person can read: what the
    agent said when it got it wrong, and what it said when it did not.
    """
    alert = next(a for a in corpus() if a.alert_id == alert_id)
    base = AgentConfig()
    changed = base.with_change(**{change: True})

    out = {
        "alert_id": alert_id, "label": alert.label, "change": change,
        "scenario": alert.scenario, "party": alert.party.name,
        "description": alert.description, "arms": [],
        # The evidence a person can read for themselves, straight off the alert.
        "occupation": alert.party.occupation,
        "annual_income": alert.party.annual_income,
        "transactions": [
            {"date": t.date, "ref": t.ref, "amount": t.amount,
             "direction": t.direction, "medium": t.medium}
            for t in alert.transactions
        ],
        # The user turn is identical in both arms; only the standing
        # instructions differ, and the difference is the proposal.
        "prompt": user_turn(alert, render_alert(alert)),
        "added_rule": EXPLAIN_BEFORE_ESCALATE.strip(),
    }
    for label, config in (("before", base), ("after", changed)):
        disposition = run_alert(alert, Router(Ledger()), RunConfig(agent=config))
        verdict = disposition.verdict
        out["arms"].append({
            "arm": label,
            "flags": config.changes,
            "system": agent_system_prompt(config),
            "disposition": verdict.disposition if verdict else "unparseable",
            "confidence": verdict.confidence if verdict else None,
            "narrative": verdict.narrative if verdict else "",
            "correct": disposition.grade.correct,
            "cited": disposition.grade.cited,
        })
    before, after = out["arms"]
    out["flipped"] = (not before["correct"]) and after["correct"]
    return out



def cache_probe() -> dict:
    """Send the real system prompt twice, with a cache point, to every model.

    Bedrock bills a cached prefix at a tenth of the input rate, so the fixed
    instructions could be paid for once instead of seventy times. Whether that
    is available is not an opinion: the provider either writes the cache and
    reads it back, or it refuses the request. Both answers are recorded here,
    verbatim, with the model that gave them.
    """
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("bedrock-runtime")
    results = []
    for spec in load_fleet():
        request = {
            "modelId": spec.model,
            "system": [{"text": SYSTEM_PROMPT}, {"cachePoint": {"type": "default"}}],
            "messages": [{"role": "user",
                          "content": [{"text": "Reply with the single word OK."}]}],
            "inferenceConfig": {"maxTokens": 16, "temperature": 0.0},
        }
        calls = []
        for _ in (1, 2):
            try:
                usage = client.converse(**request)["usage"]
                calls.append({
                    "ok": True,
                    "tokens_in": usage["inputTokens"],
                    "written": usage.get("cacheWriteInputTokens", 0),
                    "read": usage.get("cacheReadInputTokens", 0),
                })
            except ClientError as exc:
                calls.append({
                    "ok": False,
                    "error": f"{exc.response['Error']['Code']}: "
                             f"{exc.response['Error']['Message']}"[:200],
                })
                break
        results.append({
            "tier": spec.tier, "model": spec.model, "serving": spec.serving,
            "price_in": spec.price_in, "calls": calls,
            "caches": bool(calls[-1].get("read")),
        })

    premium = next(m for m in load_fleet() if m.tier == "premium")
    prefix = measure_system_tokens(premium, SYSTEM_PROMPT)
    alerts = 70
    full = prefix * alerts
    return {
        "models": results,
        "prefix_tokens": prefix,
        "alerts": alerts,
        "tokens_now": full,
        "tokens_cached": round(full * CACHE_READ_RATE),
        "cache_read_rate": CACHE_READ_RATE,
        "usd_now": round(full * premium.price_in / 1_000_000, 4),
        "usd_cached": round(full * CACHE_READ_RATE * premium.price_in / 1_000_000, 4),
        "priced_on": premium.model,
    }

def token_comparison() -> dict:
    """Price the fixed instruction prefix as it stands, against what it was.

    Before the rule catalogue the thresholds were inlined for every scenario,
    whether or not the alert was about them. The earlier figure is recorded in
    the improve artifact; the current one is measured here, now.
    """
    spec = next(m for m in load_fleet() if m.tier == "premium")
    now = measure_system_tokens(spec, SYSTEM_PROMPT)
    recorded = (improve_recorded() or {}).get("system_tokens")
    alerts = 70
    saved = (recorded - now) if recorded else 0
    return {
        "tokens_now": now,
        "chars_now": len(SYSTEM_PROMPT),
        "tokens_before": recorded,
        "saved_per_call": saved,
        "saved_over_corpus": saved * alerts,
        "alerts": alerts,
        "model": spec.model,
        "price_in": spec.price_in,
        "usd_per_call_now": round(now * spec.price_in / 1e6, 8),
        "rules": rules_module.summary(),
    }


def start_ab(body: dict) -> Run:
    """Measure one proposal on a subset of alerts, live."""
    recorded = improve_recorded()
    proposals = {p["proposal_id"]: p for p in recorded.get("proposals", [])}
    raw = proposals.get(body.get("proposal_id"))
    if raw is None:
        raise KeyError("unknown proposal")
    proposal = Proposal(**raw)
    alert_ids = body.get("alert_ids") or []
    repeats = max(1, min(3, int(body.get("repeats", 1))))
    approver = (recorded.get("contract") or {}).get("approver", "")

    run = Run(phase_id="ab")
    IMPROVE_RUNS["ab"] = run

    def worker() -> None:
        try:
            for event in ab_live(corpus(), alert_ids, proposal,
                                 approver=approver, repeats=repeats):
                run.publish(event)
        except Exception as exc:
            run.publish(RouteEventShim("error", f"{type(exc).__name__}: {exc}"))
        finally:
            run.close()

    threading.Thread(target=worker, daemon=True).start()
    return run


def start_probe(alert_id: str, body: dict) -> Run:
    """Fire a payload at one alert, live, and publish each step."""
    alert = next(a for a in corpus() if a.alert_id == alert_id)
    run = Run(phase_id=alert_id)
    PROBE_RUNS[alert_id] = run
    tier = body.get("tier") or "cheap"
    mode = body.get("mode") or "paired"

    def worker() -> None:
        try:
            events = (
                sweep(alert, Router(Ledger()), pin=tier,
                      guardrail=bool(body.get("guardrail")))
                if mode == "sweep" else
                paired_probe(alert, body.get("probe_id") or "P-01",
                             Router(Ledger()), pin=tier)
            )
            for event in events:
                run.publish(event)
        except Exception as exc:
            run.publish(RouteEventShim("error", f"{type(exc).__name__}: {exc}"))
        finally:
            run.close()

    threading.Thread(target=worker, daemon=True).start()
    return run


def start_route(alert_id: str, policy: RoutingPolicy, broken: str | None) -> Run:
    """Route one alert live, publishing each step as it happens."""
    alert = next(a for a in corpus() if a.alert_id == alert_id)
    fleet = load_fleet()
    if broken:
        fleet = break_tier(fleet, broken)

    run = Run(phase_id=alert_id)
    ROUTE_RUNS[alert_id] = run

    def worker() -> None:
        try:
            for event in route_alert(alert, policy, fleet=fleet):
                run.publish(event)
        except Exception as exc:  # a live call can fail in ways we do not own
            run.publish(RouteEventShim("error", f"{type(exc).__name__}: {exc}"))
        finally:
            run.close()

    threading.Thread(target=worker, daemon=True).start()
    return run


@dataclass(frozen=True)
class RouteEventShim:
    """Shaped like a RouteEvent so the same stream plumbing carries it."""

    kind: str
    text: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "data": {}}


def save_run_summary(run: Run, model: str, withheld: bool) -> None:
    """Keep what a live run proved, so the console can show it again later.

    The raw Claude Code stream is already on disk but it is a transport log.
    This is the readable trace: the attempts, the test results, the verdict.
    """
    kept = [e for e in run.events if e["kind"] != "delta"]
    if not kept:
        return
    summary = {
        "phase_id": run.phase_id,
        "run_id": run.run_id,
        "model": model,
        "rules_withheld": withheld,
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "events": kept,
    }
    record = json.dumps(summary, indent=2)
    (LIVE_DIR / f"{run.phase_id}.run.json").write_text(record, encoding="utf-8")
    # One record per run, named by its run ID, so a delivery can carry its evidence.
    (LIVE_DIR / "runs").mkdir(exist_ok=True)
    (LIVE_DIR / "runs" / f"{run.run_id}.json").write_text(record, encoding="utf-8")


def last_run(phase_id: str) -> dict:
    """The most recent live run of a phase, if one was ever recorded here."""
    path = LIVE_DIR / f"{phase_id}.run.json"
    if not path.exists():
        return {"phase_id": phase_id, "found": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["found"] = True
    return data


def phase_state() -> list[dict]:
    recorded = {}
    record = BUILD_DIR / "build.json"
    if record.exists():
        for result in json.loads(record.read_text())["results"]:
            recorded[result["phase_id"]] = result

    state = []
    for index, phase in enumerate(order(), start=1):
        artifact = BUILD_DIR / phase.produces
        run = RUNS.get(phase.phase_id)
        state.append({
            "n": index,
            "phase_id": phase.phase_id,
            "name": phase.name,
            "produces": phase.produces,
            "gate": phase.gate,
            "kind": phase.kind,
            "verify_with": list(phase.verify_with),
            "depends_on": list(phase.depends_on),
            "markers": list(phase.markers),
            "tokens": list(phase.tokens),
            "artifact_exists": artifact.exists(),
            "artifact_chars": artifact.stat().st_size if artifact.exists() else 0,
            "recorded": recorded.get(phase.phase_id, {}).get("evaluation"),
            "recorded_cost": recorded.get(phase.phase_id, {}).get("cost_usd"),
            "live_running": bool(run and not run.finished),
            "live_done": bool(run and run.finished),
        })
    return state


def skill_state() -> list[dict]:
    """Every skill file on disk, and which stages attach it."""
    users: dict[str, list[str]] = {}
    for phase in order():
        for name in phase.skills:
            users.setdefault(name, []).append(phase.name)

    skills = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        name = path.stem
        skills.append({
            "name": name,
            "file": path.name,
            "chars": len(body),
            "lines": body.count("\n") + 1,
            "used_by": users.get(name, []),
            "headings": re.findall(r"^#+\s+(.+)$", body, re.M)[:12],
            "body": body,
        })
    return skills


def oracle_state() -> dict:
    """The acceptance suite the model never sees, named test by test."""
    body = ORACLE.read_text(encoding="utf-8") if ORACLE.exists() else ""
    names = re.findall(r"^def (test_\w+)", body, re.M)
    return {
        "path": str(ORACLE.relative_to(ROOT)).replace("\\", "/"),
        "count": len(names),
        "chars": len(body),
        "tests": [n[5:].replace("_", " ") for n in names],
        "test_names": names,
        "body": body,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in str(args[0] if args else ""):
            return

    # -- helpers ---------------------------------------------------------

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

    def _static(self, path: Path) -> None:
        """Serve one file out of the UI directory, by extension."""
        if not path.exists() or path.parent != UI_DIR:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, path.read_bytes(), MIME.get(path.suffix, "text/plain"))

    # -- routes ----------------------------------------------------------

    def do_GET(self) -> None:
        route = urlparse(self.path).path

        if route in ("/", "/factory", "/factory.html"):
            self._static(UI_DIR / "factory.html")
            return

        if route.startswith("/ui/"):
            self._static(UI_DIR / route.rsplit("/", 1)[-1])
            return

        if route == "/api/delivery":
            focus = parse_qs(urlparse(self.path).query).get("focus", [None])[0]
            self._json(delivery_state.snapshot(live_build(), focus, dict(DELIVERY) or None))
            return

        if route == "/api/state":
            current = brief_module.load()
            self._json({"connected": True, "product": current.product,
                        "build_dir": str(BUILD_DIR), "phases": phase_state(),
                        "brief": current.to_dict(),
                        "prd_path": str(brief_module.PRD_PATH)})
            return

        if route == "/api/prd":
            try:
                self._json({"body": brief_module.read_prd()})
            except FileNotFoundError as exc:
                self._json({"error": str(exc)}, 404)
            return

        if route == "/api/brief":
            self._json(brief_module.load().to_dict())
            return

        if route == "/api/tamper":
            self._json({k: tamper_state(k) for k in TAMPERS})
            return

        if route == "/api/rules":
            self._json(rules_module.summary())
            return

        if route.startswith("/api/demo/"):
            name = route.rsplit("/", 1)[-1]
            path = DEMO_DIR / name
            if path.parent != DEMO_DIR or not path.exists():
                self._json({"error": "unknown sample"}, 404)
                return
            self._json({"name": name, "body": path.read_text(encoding="utf-8")})
            return

        if route == "/api/improve/recorded":
            self._json(improve_recorded())
            return

        if route == "/api/improve/stream":
            self._stream("ab", IMPROVE_RUNS)
            return

        if route == "/api/secures/recorded":
            self._json(secures_recorded())
            return

        if route.startswith("/api/probestream/"):
            self._stream(route.rsplit("/", 1)[-1], PROBE_RUNS)
            return

        if route == "/api/alerts":
            self._json({"alerts": alert_catalogue()})
            return

        if route == "/api/runs/recorded":
            self._json(recorded_runs())
            return

        if route.startswith("/api/routestream/"):
            self._stream(route.rsplit("/", 1)[-1], ROUTE_RUNS)
            return

        if route == "/api/pillars":
            self._send(200, PILLARS.read_bytes(), "application/json")
            return

        if route == "/api/skills":
            root = str(SKILLS_DIR.relative_to(ROOT)).replace("\\", "/")
            self._json({"root": root + "/", "skills": skill_state()})
            return

        if route.startswith("/api/lastrun/"):
            self._json(last_run(route.rsplit("/", 1)[-1]))
            return

        if route == "/api/oracle":
            self._json(oracle_state())
            return

        if route.startswith("/api/prompt/"):
            # The exact text a stage would be sent, without running it.
            phase_id = route.rsplit("/", 1)[-1]
            if phase_id not in BY_ID:
                self._json({"error": "unknown phase"}, 404)
                return
            query = parse_qs(urlparse(self.path).query)
            phase = BY_ID[phase_id]
            prompt = build_prompt(
                phase, upstream_for(phase_id), brief_module.load(),
                withhold_rules=query.get("withhold", ["0"])[0] == "1",
            )
            self._json({
                "phase_id": phase_id,
                "name": phase.name,
                "skills": list(phase.skills),
                "chars": len(prompt),
                "prompt": prompt,
            })
            return

        if route.startswith("/api/artifact/"):
            phase_id = route.rsplit("/", 1)[-1]
            if phase_id not in BY_ID:
                self._json({"error": "unknown phase"}, 404)
                return
            path = BUILD_DIR / BY_ID[phase_id].produces
            body = path.read_text(encoding="utf-8") if path.exists() else ""
            self._json({"phase_id": phase_id, "chars": len(body), "body": body})
            return

        if route.startswith("/api/stream/"):
            self._stream(route.rsplit("/", 1)[-1])
            return

        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}") if length else {}

        if route == "/api/tamper":
            name = payload.get("target") or "document"
            if name not in TAMPERS:
                self._json({"error": "unknown target"}, 400)
                return
            self._json(apply_tamper(name, payload.get("action") or "break"))
            return

        if route == "/api/chat/route":
            self._json(chat_route(
                payload.get("text", ""), corpus(), Router(Ledger()),
                broken=payload.get("break_tier") or None))
            return

        if route == "/api/chat/ask":
            exchange = chat_ask(
                payload.get("text", ""), corpus(), Router(Ledger()),
                tier=payload.get("tier") or "premium")
            self._json(exchange.to_dict())
            return

        if route == "/api/chat/attack":
            # Both framings in one request, so the only thing that differs on
            # screen is where the attacker's text sits.
            text = payload.get("text", "")
            attack_text = payload.get("payload", "")
            tier = payload.get("tier") or "cheap"
            both = {}
            for state, guard in (("off", False), ("on", True)):
                if payload.get("only") and payload["only"] != state:
                    continue
                both[state] = chat_attack(
                    text, attack_text, corpus(), Router(Ledger()),
                    tier=tier, guardrail=guard,
                    probe_id=payload.get("probe_id") or "P-01",
                    prompt_only=bool(payload.get("prompt_only")),
                ).to_dict()
            self._json(both)
            return

        if route == "/api/improve/case":
            self._json(single_case(
                payload.get("alert_id") or "S90009",
                payload.get("change") or "explain_before_escalate"))
            return

        if route == "/api/prd/save":
            body_text = payload.get("body", "")
            if len(body_text.strip()) < 200:
                self._json({"error": "too short to be a requirement"}, 400)
                return
            prd = brief_module.PRD_PATH
            # Keep the previous requirement - a paste stays reversible.
            if prd.exists():
                (prd.parent / (prd.name + ".bak")).write_text(
                    prd.read_text(encoding="utf-8"), encoding="utf-8")
            prd.write_text(body_text, encoding="utf-8")
            self._json({"saved": True, "chars": len(body_text),
                        "path": prd.name, "backup": prd.name + ".bak"})
            return

        if route == "/api/improve/ab":
            running = IMPROVE_RUNS.get("ab")
            if running and not running.finished:
                self._json({"error": "already running"}, 409)
                return
            try:
                start_ab(payload)
            except KeyError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json({"started": True})
            return

        if route == "/api/improve/cache":
            # Four real calls at sixteen output tokens: two per model, so a
            # cached read has something to read.
            self._json(cache_probe())
            return

        if route == "/api/improve/tokens":
            # Two real calls at one output token each, to price the prefix.
            self._json(token_comparison())
            return

        if route.startswith("/api/probe/"):
            alert_id = route.rsplit("/", 1)[-1]
            if not any(a.alert_id == alert_id for a in corpus()):
                self._json({"error": "unknown alert"}, 404)
                return
            running = PROBE_RUNS.get(alert_id)
            if running and not running.finished:
                self._json({"error": "already running"}, 409)
                return
            start_probe(alert_id, payload)
            self._json({"started": alert_id})
            return

        if route.startswith("/api/route/"):
            alert_id = route.rsplit("/", 1)[-1]
            if not any(a.alert_id == alert_id for a in corpus()):
                self._json({"error": "unknown alert"}, 404)
                return
            existing = ROUTE_RUNS.get(alert_id)
            if existing and not existing.finished:
                self._json({"error": "already running"}, 409)
                return
            body = payload
            policy = RoutingPolicy(
                quality_floor=float(body.get("quality_floor", 0.0)),
                escalate_without_evidence=bool(
                    body.get("escalate_without_evidence", True)),
                max_escalations=int(body.get("max_escalations", 1)),
            )
            start_route(alert_id, policy, body.get("break_tier") or None)
            self._json({"started": alert_id, "policy": policy.label})
            return

        if route == "/api/deliver":
            # The factory acts up to the merge gate: commit, push, open a PR.
            try:
                done = deliver_tracked(str(payload.get("task", "")))
            except DELIVERY_FAILURES:
                self._json({"error": DELIVERY["error"]}, 409)
                return
            self._json({"branch": done.branch, "commit": done.commit, "pr_url": done.pr_url})
            return

        if route.startswith("/api/run/"):
            phase_id = route.rsplit("/", 1)[-1]
            if phase_id not in BY_ID:
                self._json({"error": "unknown phase"}, 404)
                return
            existing = RUNS.get(phase_id)
            if existing and not existing.finished:
                self._json({"error": "already running"}, 409)
                return
            start_run(phase_id, focus=bool(payload.get("focus", True)),
                      model=str(payload.get("model") or "sonnet"),
                      withhold_rules=bool(payload.get("withhold_rules")))
            self._json({"started": phase_id,
                        "deliver_to": auto_task() if BY_ID[phase_id].kind == "code" else None})
            return

        if route == "/api/extract":
            # Stage 0: read the human's requirements and structure them.
            try:
                prompt = brief_module.extraction_prompt(brief_module.read_prd())
                generation = generate(prompt)
                payload = json.loads(
                    re.search(r"\{.*\}", generation.text, re.S).group(0)
                )
            except (FileNotFoundError, BuildToolError, AttributeError,
                    json.JSONDecodeError) as exc:
                self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            extracted = brief_module.from_extraction(payload)
            brief_module.save(extracted)
            self._json({"brief": extracted.to_dict(),
                        "cost_usd": round(generation.cost_usd, 5),
                        "duration_ms": generation.duration_ms})
            return

        if route == "/api/brief":
            # The human approves or corrects what stage 0 extracted.
            try:
                approved = brief_module.from_extraction(payload)
            except (TypeError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            brief_module.save(approved)
            self._json({"saved": True, "brief": approved.to_dict()})
            return

        if route.startswith("/api/evaluate/"):
            phase_id = route.rsplit("/", 1)[-1]
            if phase_id not in BY_ID:
                self._json({"error": "unknown phase"}, 404)
                return
            phase = BY_ID[phase_id]
            if phase.kind == "code":
                # For code there is nothing to grep for: run the tests.
                outcome = run_tests(phase.verify_with, BUILD_DIR / phase.produces)
                # Name the tests that failed, so the console can point at them
                # in the list rather than only reporting a count.
                failed = re.findall(r"^FAILED\s+\S+::(\w+)", outcome.output, re.M)
                self._json({
                    "phase_id": phase_id,
                    "passed": outcome.ok,
                    "missing": [],
                    "length": (BUILD_DIR / phase.produces).stat().st_size
                    if (BUILD_DIR / phase.produces).exists() else 0,
                    "reason": outcome.summary,
                    "failed_tests": failed,
                    "tests": outcome.to_dict(),
                })
                return
            verdict = reevaluate(phase, BUILD_DIR / phase.produces)
            self._json(verdict.to_dict())
            return

        if route.startswith("/api/open/"):
            phase_id = route.rsplit("/", 1)[-1]
            if phase_id not in BY_ID:
                self._json({"error": "unknown phase"}, 404)
                return
            opened = open_in_editor(BUILD_DIR / BY_ID[phase_id].produces)
            self._json({"opened": opened})
            return

        self._send(404, b"not found", "text/plain")

    def _stream(self, key: str, registry: dict | None = None) -> None:
        run = (registry if registry is not None else RUNS).get(key)
        if run is None:
            self._json({"error": "no run for that key"}, 404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        listener: queue.Queue = queue.Queue()
        with run.lock:
            backlog = list(run.events)
            run.listeners.append(listener)
        try:
            for event in backlog:
                self._emit(event)
            if run.finished:
                self._emit({"kind": "eof"})
                return
            while True:
                event = listener.get()
                if event is None:
                    self._emit({"kind": "eof"})
                    return
                self._emit(event)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with run.lock:
                if listener in run.listeners:
                    run.listeners.remove(listener)

    def _emit(self, event: dict) -> None:
        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
        self.wfile.flush()


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"factory server on http://localhost:{PORT}")
    print(f"  artifacts {BUILD_DIR}")
    print(f"  {len(PHASES)} phases, all runnable live")
    print("  ctrl-c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
