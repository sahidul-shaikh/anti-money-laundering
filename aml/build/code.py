"""Turn a generated response into files on disk, then run the tests on them.

The acceptance test is committed and the model never sees it. That is the
whole point: a model marking its own homework proves nothing, so the gate is
a suite it did not write, executed for real.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ### FILE: src/detector.py
# ```python
# ...
# ```
FILE_BLOCK = re.compile(
    r"^#{0,6}\s*FILE:\s*(?P<path>[\w./\\-]+)\s*$\s*```[a-zA-Z]*\s*\n(?P<body>.*?)^```",
    re.M | re.S,
)


class NoFilesProduced(RuntimeError):
    """The response contained no file blocks we could write."""


@dataclass
class TestOutcome:
    passed: int
    failed: int
    errors: int
    output: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.failed == 0 and self.errors == 0

    @property
    def ran(self) -> bool:
        return (self.passed + self.failed + self.errors) > 0

    @property
    def summary(self) -> str:
        # A suite that never ran is a harness failure, and must never be
        # reported as though the generated code were at fault.
        if not self.ran:
            first = next(
                (line for line in self.output.splitlines() if line.strip()),
                "no output",
            )
            return f"the acceptance suite did not run: {first[:120]}"
        if self.errors:
            return f"{self.errors} collection errors"
        return f"{self.passed} passed, {self.failed} failed"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "ok": self.ok,
            "summary": self.summary,
            "output": self.output[-4000:],
        }


@dataclass
class WrittenFiles:
    files: dict[str, int] = field(default_factory=dict)

    @property
    def paths(self) -> list[str]:
        return sorted(self.files)


def extract_files(text: str) -> dict[str, str]:
    """Pull `FILE: path` + fenced block pairs out of a response."""
    found = {
        match.group("path").replace("\\", "/"): match.group("body")
        for match in FILE_BLOCK.finditer(text)
    }
    return {p: b for p, b in found.items() if b.strip()}


def write_files(workspace: Path, blocks: dict[str, str]) -> WrittenFiles:
    """Write the extracted files under the workspace, never outside it."""
    if not blocks:
        raise NoFilesProduced("no FILE: blocks in the response")
    written = WrittenFiles()
    for relative, body in blocks.items():
        target = (workspace / relative).resolve()
        if workspace.resolve() not in target.parents:
            raise NoFilesProduced(f"{relative} resolves outside the workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        written.files[relative] = len(body)
    return written


def run_tests(test_paths: tuple[str, ...], detector_path: Path) -> TestOutcome:
    """Run the committed acceptance suite against the generated module."""
    env = dict(os.environ, DETECTOR_PATH=str(detector_path), PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *test_paths, "-q", "--no-header",
         "--tb=short", "-p", "no:cacheprovider"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    passed = _count(output, r"(\d+) passed")
    failed = _count(output, r"(\d+) failed")
    errors = _count(output, r"(\d+) error")
    return TestOutcome(passed, failed, errors, output, completed.returncode)


def failure_feedback(outcome: TestOutcome,
                     files: dict[str, str] | None = None) -> str:
    """What to hand back to the next attempt. Its own code and the test output.

    Both halves matter. Without the files the next attempt is rewriting from
    memory, so "change only what failed" is an instruction it cannot obey.
    Without the pass count it does not know how much of the rewrite is already
    right. Nothing here is invented: the files are what it wrote and the output
    is what pytest printed.
    """
    if not outcome.ran:
        return (
            "The acceptance suite could not be executed, which is a fault in the "
            "harness rather than in your code. Return the same files again.\n\n"
            f"{outcome.output[-1500:]}"
        )
    return (
        "Your previous attempt did not pass the acceptance tests. You have not "
        "seen these tests and must not try to guess around them: fix the code so "
        "the behaviour is right.\n\n"
        f"RESULT: {outcome.summary}\n\n"
        f"{outcome.passed} of {outcome.passed + outcome.failed} checks already "
        "pass. Those parts of your implementation are correct. Change only what "
        "the failures below require, and leave every other behaviour exactly as "
        "it is - a fix that breaks a check that was passing is not a fix.\n\n"
        f"{_previous_files(files)}"
        "PYTEST OUTPUT\n"
        f"{outcome.output[-5000:]}\n\n"
        "Re-read the integration contract in the requirements, correct the "
        "implementation, and return the complete files again."
    )


def _previous_files(files: dict[str, str] | None) -> str:
    """The code the last attempt wrote, so the next one edits rather than guesses."""
    if not files:
        return ""
    blocks = "".join(
        f"--- {path} ---\n{body}\n\n" for path, body in sorted(files.items())
    )
    return (
        "WHAT YOU WROTE LAST TIME - start from this, do not rewrite it from "
        "scratch\n\n"
        f"{blocks}"
    )


def _count(text: str, pattern: str) -> int:
    found = re.findall(pattern, text)
    return int(found[-1]) if found else 0
