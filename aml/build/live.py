"""Run one phase live, streaming Claude Code's output to disk as it arrives.

The console calls this; the artifact file grows token by token while an editor
has it open. Claude Code generates every character - this module is a pipe
that tees the stream to a file and to the browser.

Claude Code's own file-writing tools are deliberately not used. They were
refused in headless mode, and teeing the stream is both smoother on screen
and keeps the write path under our control.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from aml.build.code import (
    NoFilesProduced,
    extract_files,
    failure_feedback,
    run_tests,
    write_files,
)
from aml.build.evaluator import Evaluation, evaluate
from aml.build.loop import run_loop
from aml.build.phases import PhaseSpec

MODEL = "sonnet"
TIMEOUT_S = 420

# Skips loading MCP server tool definitions the phases never use. Measured at
# roughly a fifth of the cost per phase, with no effect on the document.
BASE_FLAGS = [
    "-p",
    "--output-format", "stream-json",
    "--include-partial-messages",
    "--verbose",
    "--strict-mcp-config",
]


class LiveError(RuntimeError):
    """Claude Code could not be started or did not finish."""


@dataclass
class LiveEvent:
    kind: str          # starting | booting | delta | tool | done | error
    elapsed_s: float
    text: str = ""
    data: dict | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "elapsed_s": round(self.elapsed_s, 2),
            "text": self.text,
            "data": self.data or {},
        }


def executable() -> str:
    found = shutil.which("claude")
    if not found:
        raise LiveError("claude is not on PATH")
    return found


def run_phase_live(
    phase: PhaseSpec,
    prompt: str,
    artifact_path: Path,
    events_path: Path | None = None,
    model: str = MODEL,
    timeout: int = TIMEOUT_S,
) -> Iterator[LiveEvent]:
    """Yield events as the phase runs. The artifact file grows as they arrive."""
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("", encoding="utf-8")
    raw = events_path.open("w", encoding="utf-8") if events_path else None

    started = time.monotonic()
    now = lambda: time.monotonic() - started  # noqa: E731

    yield LiveEvent("starting", now(), data={
        "phase_id": phase.phase_id,
        "name": phase.name,
        "artifact": str(artifact_path),
        "prompt_chars": len(prompt),
        "prompt": prompt,
        "markers": list(phase.markers),
        "tokens": list(phase.tokens),
        "model": model,
    })

    process = subprocess.Popen(
        [executable(), *BASE_FLAGS, "--model", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    process.stdin.write(prompt)
    process.stdin.close()

    cost = 0.0
    turns = 0
    booted = False
    written = 0
    with artifact_path.open("a", encoding="utf-8") as sink:
        for line in process.stdout:
            if now() > timeout:
                process.kill()
                yield LiveEvent("error", now(), "timed out")
                break
            line = line.strip()
            if not line:
                continue
            if raw:
                raw.write(line + "\n")
                raw.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = event.get("type")
            inner = event.get("event", {}) if kind == "stream_event" else {}

            if inner.get("type") == "content_block_delta":
                chunk = inner.get("delta", {}).get("text", "")
                if not chunk:
                    continue
                if not booted:
                    booted = True
                    yield LiveEvent("booting", now(), "first token",
                                    data={"boot_s": round(now(), 1)})
                sink.write(chunk)
                sink.flush()
                written += len(chunk)
                yield LiveEvent("delta", now(), chunk, data={"written": written})

            elif kind == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        yield LiveEvent("tool", now(), block.get("name", ""),
                                        data={"input": str(block.get("input"))[:200]})

            elif kind == "result":
                cost = float(event.get("total_cost_usd", 0.0))
                turns = int(event.get("num_turns", 0))
                if event.get("is_error"):
                    yield LiveEvent("error", now(), str(event.get("result"))[:300])

    process.wait()
    if raw:
        raw.close()

    body = artifact_path.read_text(encoding="utf-8")
    verdict = evaluate(phase, body)
    yield LiveEvent("done", now(), data={
        "cost_usd": round(cost, 5),
        "turns": turns,
        "chars": len(body),
        "duration_s": round(now(), 1),
        "evaluation": verdict.to_dict(),
        "exit_code": process.returncode,
    })


def reevaluate(phase: PhaseSpec, artifact_path: Path) -> Evaluation:
    """Grade whatever is on disk right now, including a hand-edited file."""
    if not artifact_path.exists():
        return Evaluation(phase.phase_id, False, tuple(phase.markers), 0,
                          "no artifact on disk")
    return evaluate(phase, artifact_path.read_text(encoding="utf-8"))


def drain(
    events: Iterator[LiveEvent], on_event: Callable[[LiveEvent], None]
) -> LiveEvent | None:
    """Consume a run, handing each event to a callback. Returns the last one."""
    last = None
    for event in events:
        on_event(event)
        last = event
    return last


# -- code phases --------------------------------------------------------


def _stream_once(
    prompt: str, sink_path: Path, model: str, timeout: int, emit
) -> tuple[str, float, float]:
    """One Claude Code call. Returns the full text, its cost and its duration."""
    started = time.monotonic()
    sink_path.parent.mkdir(parents=True, exist_ok=True)
    sink_path.write_text("", encoding="utf-8")
    process = subprocess.Popen(
        [executable(), *BASE_FLAGS, "--model", model],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    process.stdin.write(prompt)
    process.stdin.close()

    collected: list[str] = []
    cost = 0.0
    with sink_path.open("a", encoding="utf-8") as sink:
        for line in process.stdout:
            if time.monotonic() - started > timeout:
                process.kill()
                break
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            inner = event.get("event", {}) if event.get("type") == "stream_event" else {}
            if inner.get("type") == "content_block_delta":
                chunk = inner.get("delta", {}).get("text", "")
                if chunk:
                    collected.append(chunk)
                    sink.write(chunk)
                    sink.flush()
                    emit(chunk)
            elif event.get("type") == "result":
                cost = float(event.get("total_cost_usd", 0.0))
    process.wait()
    return "".join(collected), cost, time.monotonic() - started


def run_code_phase_live(
    phase: PhaseSpec,
    prompt: str,
    workspace: Path,
    events_path: Path | None = None,
    model: str = MODEL,
    timeout: int = TIMEOUT_S,
    max_attempts: int = 3,
) -> Iterator[LiveEvent]:
    """Generate code, run the acceptance suite, and iterate on what it says."""
    started = time.monotonic()
    now = lambda: time.monotonic() - started  # noqa: E731
    pending: list[LiveEvent] = []
    detector = workspace / phase.produces
    stream_sink = (events_path.parent if events_path else workspace) / f"{phase.phase_id}.stream.md"

    yield LiveEvent("starting", now(), data={
        "phase_id": phase.phase_id, "name": phase.name, "artifact": str(detector),
        "prompt_chars": len(prompt), "prompt": prompt,
        "markers": [], "tokens": [],
        "model": model, "kind": "code",
        "verify_with": list(phase.verify_with), "max_attempts": max_attempts,
    })

    def act(feedback: str | None) -> tuple[list[str], float, float]:
        turn = prompt if feedback is None else f"{prompt}\n\n{feedback}"
        pending.append(LiveEvent("attempt", now(), f"attempt {len(state['attempts']) + 1}",
                                 data={"has_feedback": feedback is not None}))
        text, cost, duration = _stream_once(
            turn, stream_sink, model, timeout, lambda c: pending.append(
                LiveEvent("delta", now(), c)))
        try:
            written = write_files(workspace, extract_files(text))
        except NoFilesProduced as exc:
            pending.append(LiveEvent("error", now(), str(exc)))
            return [], cost, duration
        state["files"] = written.paths
        pending.append(LiveEvent("files", now(), ", ".join(written.paths),
                                 data={"files": written.files}))
        return written.paths, cost, duration

    def verify() -> tuple[bool, str]:
        outcome = run_tests(phase.verify_with, detector)
        state["last"] = outcome
        pending.append(LiveEvent("tests", now(), outcome.summary,
                                 data=outcome.to_dict()))
        return outcome.ok, outcome.output

    state: dict = {"attempts": [], "last": None, "files": []}
    result_holder: dict = {}

    def on_attempt(attempt) -> None:
        state["attempts"].append(attempt)

    # The loop is synchronous; drain its events between steps so the console
    # sees each attempt as it happens rather than all at the end.
    import threading

    def worker() -> None:
        result_holder["result"] = run_loop(
            act, verify, max_attempts=max_attempts,
            feedback=failure_feedback_from(state, workspace), on_attempt=on_attempt,
        )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    while thread.is_alive() or pending:
        while pending:
            yield pending.pop(0)
        if thread.is_alive():
            time.sleep(0.05)

    result = result_holder.get("result")
    outcome = state.get("last")
    yield LiveEvent("done", now(), data={
        "cost_usd": round(result.cost_usd if result else 0.0, 5),
        "turns": result.iterations if result else 0,
        "chars": detector.stat().st_size if detector.exists() else 0,
        "duration_s": round(now(), 1),
        "evaluation": {
            "phase_id": phase.phase_id,
            "passed": bool(result and result.passed),
            "missing": [],
            "length": detector.stat().st_size if detector.exists() else 0,
            "reason": (outcome.summary if outcome else "no tests run")
            + (f" after {result.iterations} attempt(s)" if result else ""),
        },
        "loop": result.to_dict() if result else {},
        "exit_code": 0 if result and result.passed else 1,
    })


def failure_feedback_from(state: dict, workspace: Path):
    """Hand the last attempt its own files and the pytest output they produced."""
    def build(_detail: str) -> str:
        outcome = state.get("last")
        if not outcome:
            return ""
        written = {
            path: (workspace / path).read_text(encoding="utf-8")
            for path in state.get("files", [])
            if (workspace / path).exists()
        }
        return failure_feedback(outcome, written)
    return build
