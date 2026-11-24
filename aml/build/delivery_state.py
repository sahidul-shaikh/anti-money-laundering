"""The delivery chain per task, read from what actually happened.

Sources, all read at request time: the task files under tasks/, the run
records under artifacts/live/runs/, and the pull requests on GitHub (their
commits carry the provenance trailers, their checks are CI, their reviews are
the human decision). Nothing here writes, and nothing advances on a timer.

Stations: intent, plan, loop, commit, pr, ci, approval, merged.
States: done, running, waiting, failed, pending, manual, override.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from aml.build.deliver import REPO, ROOT

TASKS_DIR = ROOT / "tasks"
RUNS_DIR = ROOT / "artifacts" / "live" / "runs"
PR_FIELDS = ("number,title,url,author,state,createdAt,mergedAt,mergedBy,"
             "headRefName,reviews,statusCheckRollup,commits")
TASK_TITLE = re.compile(r"^(T-\d{3})\b")
CACHE_S = 10
# GitHub caps a query at 500,000 nodes; PRs x commits x authors at 30 PRs is
# 300,000. Older PRs beyond the 30 most recent are not shown.
PR_LIMIT = 30
_cache: dict = {"at": 0.0, "prs": []}


def station(state: str, label: str, detail: str = "", link: str = "",
            since: str = "") -> dict:
    return {"state": state, "label": label, "detail": detail, "link": link, "since": since}


# -- pure derivation ------------------------------------------------------


def trailers(message: str) -> dict[str, str]:
    """Key: value lines from a commit message."""
    found = re.findall(r"^([A-Z][A-Za-z-]+): (.+)$", message, re.M)
    return {k: v.strip() for k, v in found}


def ci_station(pr: dict | None) -> dict:
    if not pr:
        return station("pending", "CI")
    checks = pr.get("statusCheckRollup") or []
    if not checks:
        return station("pending", "CI", "no checks yet")
    running = [c for c in checks if c.get("status") != "COMPLETED"]
    failed = [c["name"] for c in checks if c.get("conclusion") not in (None, "SUCCESS", "SKIPPED")]
    names = ", ".join(c["name"] for c in checks)
    if failed:
        return station("failed", "CI", "failed: " + ", ".join(failed), pr["url"] + "/checks")
    if running:
        since = min(c.get("startedAt") or "" for c in running)
        return station("running", "CI", f"{len(running)} of {len(checks)} running", pr["url"] + "/checks", since)
    return station("done", "CI", f"{names} passed", pr["url"] + "/checks")


def approval_station(pr: dict | None, ci: dict) -> dict:
    if not pr:
        return station("pending", "Human approval")
    approved = [r for r in pr.get("reviews") or [] if r.get("state") == "APPROVED"]
    if approved:
        last = approved[-1]
        return station("done", "Human approval", f"approved by {last['author']['login']}",
                       pr["url"], last.get("submittedAt", ""))
    if pr["state"] == "OPEN" and ci["state"] == "done":
        return station("waiting", "Human approval", "waiting for a human", pr["url"], pr["createdAt"])
    if pr["state"] == "MERGED":
        return station("override", "Human approval", "no approving review", pr["url"])
    return station("pending", "Human approval")


def merged_station(pr: dict | None, approval: dict) -> dict:
    if not pr:
        return station("pending", "Merged")
    if pr["state"] == "MERGED":
        who = (pr.get("mergedBy") or {}).get("login", "")
        if approval["state"] == "override":
            return station("override", "Merged", f"owner override by {who}", pr["url"], pr["mergedAt"])
        return station("done", "Merged", f"merged by {who}", pr["url"], pr["mergedAt"])
    if pr["state"] == "CLOSED":
        return station("failed", "Merged", "closed without merging", pr["url"])
    return station("pending", "Merged")


def loop_station(commits: list[dict], live: dict | None, recorded: set[str]) -> dict:
    """A run counts as a loop run only if its record exists; a run ID alone proves nothing."""
    if live:
        return station("running", "Build loop",
                       f"attempt {live.get('attempt', 1)} of {live.get('max_attempts', 3)}",
                       "", live.get("started_at", ""))
    with_run = [c for c in commits if c["trailers"].get("Run-Id") in recorded]
    if with_run:
        t = with_run[-1]["trailers"]
        return station("done", "Build loop",
                       f"{t['Run-Id']} - attempts {t['Attempts']} - ${t['Cost-USD'].split()[0]}",
                       f"https://github.com/{REPO}/blob/main/artifacts/live/runs/{t['Run-Id']}.json")
    if commits:
        return station("manual", "Build loop", "interactive session, no loop run")
    return station("pending", "Build loop")


def chain(task: dict, prs: list[dict], live: dict | None = None,
          recorded: set[str] = frozenset()) -> list[dict]:
    """The eight stations for one task. `prs` are the task's PRs, oldest first;
    `recorded` is the run IDs that have a run record on disk."""
    pr = next((p for p in reversed(prs) if p["state"] == "OPEN"), prs[-1] if prs else None)
    commits = [c for p in prs for c in p["commits"] if c["trailers"].get("Task") == task["id"]]
    code = [c for c in commits if c["trailers"].get("Stage") not in (None, "plan")]
    ci = ci_station(pr)
    approval = approval_station(pr, ci)
    return [
        station("done" if task["intent_status"] == "accepted" else "waiting", "Intent",
                f"{task['intent_author']} - {task['intent_status']}"),
        station("done" if task["plan_status"].startswith("accepted") else
                "waiting" if task["plan_status"] else "pending", "Plan", task["plan_status"]),
        loop_station(code, live, recorded),
        station("done", "Commit", f"{code[-1]['oid'][:7]} by {code[-1]['author']}")
        if code else station("pending", "Commit"),
        station("done", "Pull request", f"#{pr['number']} by {pr['author']['login']}", pr["url"],
                pr["createdAt"]) if pr else station("pending", "Pull request"),
        ci,
        approval,
        merged_station(pr, approval),
    ]


def shape_pr(raw: dict) -> dict:
    """A gh PR record with each commit's trailers parsed."""
    raw["commits"] = [{
        "oid": c["oid"], "headline": c["messageHeadline"],
        "author": (c.get("authors") or [{}])[0].get("login") or "unknown",
        "trailers": trailers(c.get("messageBody") or ""),
    } for c in raw.get("commits") or []]
    return raw


# -- gathering ------------------------------------------------------------


def _status(path: Path) -> str:
    match = re.search(r"Status: ([^.\n]+)", path.read_text(encoding="utf-8")) if path.exists() else None
    return match.group(1).strip() if match else ""


def read_tasks() -> list[dict]:
    tasks = []
    for folder in sorted(TASKS_DIR.glob("T-*")):
        intent = folder / "intent.md"
        head = intent.read_text(encoding="utf-8").splitlines()[0] if intent.exists() else ""
        author = re.search(r"Author: ([^.]+)\.", intent.read_text(encoding="utf-8")) if intent.exists() else None
        tasks.append({
            "id": folder.name,
            "title": head.split(":", 1)[-1].strip(),
            "intent_status": _status(intent),
            "intent_author": author.group(1) if author else "",
            "plan_status": _status(folder / "plan.md"),
        })
    return tasks


def read_prs() -> list[dict]:
    """All PRs, oldest first, cached for CACHE_S seconds."""
    if time.monotonic() - _cache["at"] > CACHE_S:
        out = subprocess.run(
            ["gh", "pr", "list", "--repo", REPO, "--state", "all", "--limit", str(PR_LIMIT),
             "--json", PR_FIELDS],
            capture_output=True, text=True, check=True, encoding="utf-8",
        ).stdout
        _cache["prs"] = sorted((shape_pr(p) for p in json.loads(out)), key=lambda p: p["number"])
        _cache["at"] = time.monotonic()
    return _cache["prs"]


def snapshot(live: dict | None = None) -> dict:
    """Every task's chain, the focus task, and PRs that belong to no task."""
    tasks = read_tasks()
    prs = read_prs()
    by_task: dict[str, list[dict]] = {}
    unmatched = []
    for pr in prs:
        m = TASK_TITLE.match(pr["title"])
        (by_task.setdefault(m.group(1), []) if m else unmatched).append(pr)
    recorded = {p.stem for p in RUNS_DIR.glob("*.json")}
    open_tasks = [t for t in tasks if not any(p["state"] == "MERGED" for p in by_task.get(t["id"], []))]
    focus = (open_tasks or tasks or [{"id": None}])[-1]["id"]
    return {
        "focus": focus,
        "tasks": [{**t, "prs": [{"number": p["number"], "url": p["url"], "state": p["state"],
                                 "author": p["author"]["login"], "title": p["title"],
                                 "commits": p["commits"]} for p in by_task.get(t["id"], [])],
                   "chain": chain(t, by_task.get(t["id"], []),
                                  live if t["id"] == focus else None, recorded)}
                  for t in tasks],
        "unmatched": [{"number": p["number"], "title": p["title"], "url": p["url"], "state": p["state"]}
                      for p in unmatched],
    }
