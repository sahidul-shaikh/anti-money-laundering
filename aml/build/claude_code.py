"""Run Claude Code headless to produce one phase artifact.

This is the part of the demonstration where the factory genuinely builds. The
artifacts are not fixtures written in advance: each one is generated here, from
the brief and from what the earlier phases produced, and the cost and token
count come back from the run itself.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

TIMEOUT_S = 600
MODEL = "sonnet"


def executable() -> str:
    """The Claude Code entry point for this platform.

    On Windows the npm install puts a .cmd shim next to the POSIX script, and
    CreateProcess can only run the former.
    """
    found = shutil.which("claude")
    if not found:
        raise BuildToolError("claude is not on PATH")
    return found


class BuildToolError(RuntimeError):
    """Claude Code did not return a usable result."""


@dataclass(frozen=True)
class Generation:
    text: str
    cost_usd: float
    duration_ms: int
    turns: int
    session_id: str
    model: str


def generate(prompt: str, model: str = MODEL, timeout: int = TIMEOUT_S) -> Generation:
    """One headless Claude Code invocation, with its own cost recorded."""
    # The prompt goes in on stdin, not as an argument. On Windows the npm
    # entry point is a .cmd shim, and cmd.exe mangles a long multi-line
    # argument - the model receives a fragment and answers the wrong question.
    try:
        completed = subprocess.run(
            [executable(), "-p", "--output-format", "json", "--model", model,
             "--strict-mcp-config"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise BuildToolError(f"claude timed out after {timeout}s") from exc

    if completed.returncode != 0:
        raise BuildToolError(
            f"claude exited {completed.returncode}: {completed.stderr[:300]}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BuildToolError(f"claude returned non-JSON: {completed.stdout[:200]}") from exc

    if payload.get("is_error"):
        raise BuildToolError(f"claude reported an error: {payload.get('result')}")

    return Generation(
        text=payload.get("result", ""),
        cost_usd=float(payload.get("total_cost_usd", 0.0)),
        duration_ms=int(payload.get("duration_ms", 0)),
        turns=int(payload.get("num_turns", 0)),
        session_id=payload.get("session_id", ""),
        model=model,
    )
