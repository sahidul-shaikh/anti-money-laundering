"""Deliver a passing build run as a pull request, as aml-factory-bot.

The factory acts up to the merge gate and no further: it commits, pushes a
branch and opens a pull request. Approval and merge stay with a human, and
branch protection makes that a property of the repository, not a promise.

Work happens in a temporary git worktree based on origin/main, so the
person's own checkout is never switched or touched.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aml.build import bot

REPO = "sahidul-shaikh/anti-money-laundering"
ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = Path("artifacts/builds/aml-alert-investigator")
LIVE_DIR = ROOT / "artifacts" / "live"
ACCEPTANCE = "checks/acceptance/test_detector_contract.py"
SCAN = ROOT / "scripts" / "check_no_real_data.py"


class NotDeliverable(RuntimeError):
    """The run, task or repository state does not allow delivery."""


@dataclass(frozen=True)
class Delivery:
    branch: str
    commit: str
    pr_url: str


def load_run(phase: str) -> dict:
    """The recorded summary of the latest live run of a phase."""
    path = LIVE_DIR / f"{phase}.run.json"
    if not path.exists():
        raise NotDeliverable(f"no recorded run for {phase}")
    return json.loads(path.read_text(encoding="utf-8"))


def done_event(run: dict) -> dict:
    return next((e["data"] for e in run["events"] if e["kind"] == "done"), {})


def check_task(task: str) -> None:
    """Refuse a task that does not accept the build loop's output.

    The loop always produces the structuring detector. Filing it under a task
    whose intent asked for something else puts a false record in git.
    """
    intent = ROOT / "tasks" / task / "intent.md"
    if not intent.exists():
        raise NotDeliverable(f"no intent for {task} at tasks/{task}/intent.md")
    if not re.search(r"^Delivery: factory\b", intent.read_text(encoding="utf-8"), re.M):
        raise NotDeliverable(f"{task} does not accept factory deliveries "
                             "(its intent has no 'Delivery: factory' line)")


def check_deliverable(run: dict) -> None:
    """Refuse anything that did not pass, or cannot be traced to its run."""
    if not run.get("run_id"):
        raise NotDeliverable("run has no run ID (recorded before run IDs existed)")
    if not done_event(run).get("loop", {}).get("passed"):
        raise NotDeliverable(f"run {run['run_id']} did not pass the acceptance suite")
    if not (ROOT / record_path(run)).exists():
        raise NotDeliverable(f"no run record at {record_path(run).as_posix()}")


def attempts_line(run: dict) -> str:
    """Per-attempt acceptance results, in order, from the run's test events."""
    results = [e["data"] for e in run["events"] if e["kind"] == "tests"]
    parts = []
    for n, r in enumerate(results, start=1):
        failed = f" {r['failed']} failed" if r["failed"] else ""
        parts.append(f"{n}: {r['passed']} passed{failed}")
    return f"{len(results)} ({'; '.join(parts)})"


def trailers(run: dict, task: str) -> str:
    """Provenance carried by the commit, every value taken from the run record."""
    loop = done_event(run)["loop"]
    return "\n".join([
        f"Task: {task}",
        f"Stage: {run['phase_id']}",
        f"Model: {run['model']}",
        f"Run-Id: {run['run_id']}",
        f"Attempts: {attempts_line(run)}",
        f"Cost-USD: {loop['cost_usd']} (reported by Claude Code)",
        f"Verified-By: {ACCEPTANCE}",
    ] + ([f"Plan: {plan_path(run).as_posix()}",
          f"Plan-Accepted-By: {run['plan']['accepted_by']}"] if run.get("plan") else []))


def plan_path(run: dict) -> Path:
    """Where the plan accepted for a run is delivered, beside its run record."""
    return Path("artifacts/live/runs") / f"{run['run_id']}.plan.md"


def plan_markdown(run: dict, task: str) -> str:
    """The accepted plan as a file: what was planned, by whom, and who accepted it."""
    p = run["plan"]
    return (f"# Plan for run {run['run_id']} ({task})\n\n"
            f"Drafted by: {p['model']} in {p['duration_s']} s, ${p['cost_usd']} "
            "(reported by Claude Code)\n"
            f"Accepted by: {p['accepted_by']} at {p['accepted_at']}\n\n{p['text']}\n")


def record_path(run: dict) -> Path:
    """Where a run's own record lives, relative to the repository root."""
    return Path("artifacts/live/runs") / f"{run['run_id']}.json"


def final_files(run: dict) -> list[str]:
    """What the passing attempt wrote, relative to the build directory."""
    return done_event(run)["loop"]["attempts"][-1]["produced"]


class GitFailed(RuntimeError):
    """A git command failed; carries git's own message, never a credential."""


def _git(args: list[str], cwd: Path, secret: str | None = None) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        env=bot.git_env(secret) if secret else None,
    )
    if done.returncode != 0:
        raise GitFailed(f"git {' '.join(args)} failed: {(done.stderr or done.stdout).strip()[-800:]}")
    return done.stdout.strip()


def _pr_body(run: dict, task: str) -> str:
    loop = done_event(run)["loop"]
    rows = "\n".join(
        f"| {a['number']} | {a['outcome']} | {a['duration_s']} s | ${a['cost_usd']} |"
        for a in loop["attempts"]
    )
    return (
        f"Delivered by the factory from run `{run['run_id']}` for "
        f"[{task}](https://github.com/{REPO}/blob/main/tasks/{task}/intent.md).\n\n"
        "| Attempt | Acceptance | Duration | Cost |\n|---|---|---|---|\n"
        f"{rows}\n\n"
        f"Model `{run['model']}`. Total ${loop['cost_usd']}, as reported by Claude Code. "
        f"Verified by `{ACCEPTANCE}`, a suite the model never sees.\n\n"
        + (f"**Plan accepted by {run['plan']['accepted_by']}** at {run['plan']['accepted_at']} "
           f"before the build started: `{plan_path(run).as_posix()}`.\n\n" if run.get("plan") else "")
        + "The author of this PR cannot approve or merge it. Merging requires a "
        "human approval and both required checks."
    )


def deliver(task: str, phase: str = "development",
            on_step: Callable[..., None] = lambda step, **detail: None) -> Delivery:
    """Commit, push and open a PR for the latest passing run of a phase.

    `on_step` is told as the work moves on - "commit" (committing, scanning,
    pushing) then "pr" (opening the pull request) - so a console can show it.
    """
    check_task(task)
    run = load_run(phase)
    check_deliverable(run)
    on_step("commit", run_id=run["run_id"])
    secret = bot.verified_token()
    branch = f"factory/{task.lower()}-{run['run_id']}"
    # A run is delivered once, under one task; its branch is the record of that.
    heads = _git(["ls-remote", "--heads", "origin"], ROOT).splitlines()
    earlier = [h.split("refs/heads/")[-1] for h in heads if h.endswith(f"-{run['run_id']}")]
    if earlier:
        raise NotDeliverable(f"run {run['run_id']} was already delivered as {earlier[0]}")

    _git(["fetch", "-q", "origin", "main"], ROOT)
    workdir = Path(tempfile.mkdtemp(prefix="aml-deliver-"))
    tree = workdir / "tree"
    try:
        _git(["worktree", "add", "-q", "-b", branch, str(tree), "origin/main"], ROOT)
        # The generated files, and the run record their trailers summarise.
        shipped = [BUILD_DIR / name for name in final_files(run)] + [record_path(run)]
        for relative in shipped:
            target = tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
            _git(["add", str(relative)], tree)
        if run.get("plan"):
            (tree / plan_path(run)).write_text(plan_markdown(run, task), encoding="utf-8")
            _git(["add", str(plan_path(run))], tree)
        title = f"{task}: {phase} output from run {run['run_id']}"
        message = f"{title}\n\n{trailers(run, task)}\n"
        _git(["commit", "-q", "-m", message], tree, secret)
        commit = _git(["rev-parse", "HEAD"], tree)
        scan = subprocess.run([sys.executable, str(SCAN), commit], cwd=ROOT)
        if scan.returncode != 0:
            raise NotDeliverable("real customer data in the delivery; nothing pushed")
        # The primary checkout's hooks, not the base branch's copy in the worktree.
        hooks = f"core.hooksPath={ROOT / '.githooks'}"
        _git(["-c", hooks, "push", "-q", "-u", "origin", branch], tree, secret)
    finally:
        # Cleanup must never mask the failure that brought us here.
        for args in (["worktree", "remove", "--force", str(tree)], ["branch", "-q", "-D", branch]):
            subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
        shutil.rmtree(workdir, ignore_errors=True)

    on_step("pr", commit=commit)
    pr_url = subprocess.run(
        ["gh", "pr", "create", "--repo", REPO, "--base", "main", "--head", branch,
         "--title", title, "--body", _pr_body(run, task)],
        env=bot.gh_env(secret), capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Delivery(branch=branch, commit=commit, pr_url=pr_url)
