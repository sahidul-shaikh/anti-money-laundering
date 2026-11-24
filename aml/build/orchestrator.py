"""Run the twelve phases as a graph, with a human gate and a real evaluator.

A phase runs only when everything it depends on has passed. Its output is
evaluated before anything downstream may read it, and a gated phase waits for
a named human. A failed evaluation stops the build where it stands rather
than carrying a hole forward.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from aml.build.brief import ProductBrief
from aml.build.brief import load as load_brief
from aml.build.brief import read_prd
from aml.build.claude_code import BuildToolError, Generation, generate
from aml.build.evaluator import Evaluation, evaluate
from aml.build.library import Library
from aml.build.phases import PHASES, PhaseSpec, order

WORKSPACE = Path(__file__).resolve().parents[2] / "artifacts" / "builds"


class GateBlocked(RuntimeError):
    """A phase did not pass, or a human did not approve it."""


@dataclass
class PhaseResult:
    phase_id: str
    name: str
    artifact_path: str
    evaluation: Evaluation
    cost_usd: float
    duration_ms: int
    approved_by: str = ""
    gated: bool = False
    assets_created: list[str] = field(default_factory=list)
    assets_inherited: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "artifact": self.artifact_path,
            "evaluation": self.evaluation.to_dict(),
            "cost_usd": round(self.cost_usd, 5),
            "duration_ms": self.duration_ms,
            "gated": self.gated,
            "approved_by": self.approved_by,
            "assets_created": self.assets_created,
            "assets_inherited": self.assets_inherited,
        }


def build_prompt(
    phase: PhaseSpec,
    upstream: dict[str, str],
    brief: ProductBrief | None = None,
    library: Library | None = None,
    withhold_rules: bool = False,
    plan: str = "",
) -> str:
    """The human's intent, this stage's brief, what upstream produced, and the
    plan a person accepted for this run, if there is one."""
    brief = brief or load_brief()
    # The brief's constraints are extracted from the same requirements that
    # withholding leaves out, and restate them. A withheld code stage gets
    # the preamble without them, or the handicap withholds nothing.
    withheld = withhold_rules and phase.kind == "code"
    parts = [
        brief.preamble(include_constraints=not withheld),
        "",
        f"YOUR STAGE: {phase.name}",
        f"BRIEF: {phase.brief}",
        "",
    ]
    if phase.markers:
        parts.append(
            "Your output must contain these exact section headings, in capitals: "
            + ", ".join(phase.markers) + "."
        )
    if phase.tokens:
        parts.append(
            "It must also use these identifiers in the text: "
            + ", ".join(phase.tokens) + "."
        )
    parts += [
        "Write the document only. No preamble, no commentary, no code fences "
        "around the whole thing. Markdown headings are fine."
        if phase.kind == "document" else
        "Return only the FILE: blocks described above.",
        "Be concrete and numerate. This document is read by engineers and by a "
        "model risk reviewer.",
    ]
    if phase.skills:
        # The skill is the reusable asset: how this discipline is done, written
        # once and inherited by every product the factory builds.
        library = library or Library()
        parts += ["", "HOW THIS DISCIPLINE IS DONE", ""]
        for name, body in library.skills_for(phase.skills).items():
            parts += [f"--- skill: {name} ---", body, ""]

    if phase.kind == "code":
        # The integration contract, the boundaries and the output keys are all
        # specified in the requirements. A stage that writes code reads them in
        # full rather than working from a one-line signature.
        #
        # withhold_rules exists to demonstrate the loop. It hands over the
        # signature and the output keys - without those nothing could compile
        # against the caller - but keeps back the boundary, window and direction
        # semantics. The first attempt then has to guess, the acceptance suite
        # corrects it, and the second attempt is written against real feedback.
        # It is a handicap, and the console says so.
        parts += (
            ["", "THE INTEGRATION CONTRACT (the detailed rules are withheld)", "",
             withheld_contract(), ""]
            if withhold_rules else
            ["", "THE REQUIREMENTS, IN FULL", "", read_prd(), ""]
        )
    if upstream:
        parts += ["", "WHAT EARLIER STAGES PRODUCED", ""]
        for phase_id, body in upstream.items():
            parts += [f"--- {phase_id} ---", body[:6000], ""]
    if plan:
        parts += ["", "THE PLAN A PERSON ACCEPTED FOR THIS RUN - implement against it", "", plan, ""]
    return "\n".join(parts)


WITHHELD_CONTRACT = """Implement the Actimize AML-STR structuring rule.

Signature, which the existing pipeline calls and you may not change:

    def detect_structuring(
        transactions: list[dict],
        lower_bound: float = 8000.0,
        upper_bound: float = 9999.99,
        occurrences: int = 3,
        window_days: int = 14,
    ) -> dict

Each transaction dict has: date (YYYYMMDD), ref, amount, direction.

Return a dict with exactly these keys: detected, occurrences, window_start,
window_end, refs, total.

The detailed rule semantics - how the bounds and the window behave at their
edges, which directions count, and what the counts mean when the rule does not
fire - are NOT provided here, and neither are the output conventions the
downstream system expects. Use your judgement. An acceptance suite you cannot
see will tell you where you were wrong."""


def withheld_contract() -> str:
    """Only what the caller needs, with the rule semantics left out."""
    return WITHHELD_CONTRACT

def auto_approve(phase: PhaseSpec, evaluation: Evaluation, artifact: str) -> str:
    """Stand-in approver for unattended runs."""
    return "unattended run"


def build(
    product: str,
    workspace: Path | None = None,
    library: Library | None = None,
    approver: Callable[[PhaseSpec, Evaluation, str], str] = auto_approve,
    generator: Callable[[str], Generation] = None,
    phases: list[PhaseSpec] | None = None,
    on_phase: Callable[[PhaseResult], None] | None = None,
) -> dict:
    """Run the build. Returns the record; raises GateBlocked if a phase fails."""
    workspace = (workspace or WORKSPACE) / product
    workspace.mkdir(parents=True, exist_ok=True)
    library = library or Library()
    library.begin_build()
    generator = generator or (lambda prompt: generate(prompt))
    phases = phases or order()

    artifacts: dict[str, str] = {}
    results: list[PhaseResult] = []
    passed: set[str] = set()

    for phase in phases:
        blocked = [d for d in phase.depends_on if d not in passed]
        if blocked:
            raise GateBlocked(
                f"{phase.phase_id}: cannot start, waiting on {', '.join(blocked)}"
            )

        created, inherited = [], []
        for asset in phase.assets:
            _, was_inherited = library.acquire(
                asset, {"asset": asset, "phase": phase.phase_id, "product": product}
            )
            (inherited if was_inherited else created).append(asset)

        upstream = {d: artifacts[d] for d in phase.depends_on}
        try:
            generation = generator(build_prompt(phase, upstream))
        except BuildToolError as exc:
            raise GateBlocked(f"{phase.phase_id}: build tool failed: {exc}") from exc

        path = workspace / phase.produces
        # A code phase produces a nested path, so the directory may not exist.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generation.text, encoding="utf-8")

        evaluation = evaluate(phase, generation.text)
        result = PhaseResult(
            phase_id=phase.phase_id,
            name=phase.name,
            artifact_path=str(path.relative_to(workspace.parents[1])),
            evaluation=evaluation,
            cost_usd=generation.cost_usd,
            duration_ms=generation.duration_ms,
            gated=phase.gate,
            assets_created=created,
            assets_inherited=inherited,
        )

        if not evaluation.passed:
            results.append(result)
            _write(workspace, product, results, library,
                   partial=len(results) < len(PHASES))
            raise GateBlocked(
                f"{phase.phase_id} ({phase.name}): blocked: {evaluation.reason}"
            )

        if phase.gate:
            result.approved_by = approver(phase, evaluation, generation.text)
            if not result.approved_by:
                results.append(result)
                _write(workspace, product, results, library,
                       partial=len(results) < len(PHASES))
                raise GateBlocked(f"{phase.phase_id}: not approved by a human")

        artifacts[phase.phase_id] = generation.text
        passed.add(phase.phase_id)
        results.append(result)
        if on_phase:
            on_phase(result)

    return _write(workspace, product, results, library, partial=len(phases) < len(PHASES))


def _write(
    workspace: Path,
    product: str,
    results: list[PhaseResult],
    library: Library,
    partial: bool = False,
) -> dict:
    """Write the build record.

    A run of fewer than all twelve phases writes somewhere else. Otherwise
    experimenting with --phases silently destroys the full record the console
    and the guide are built on, which is exactly what happened once.
    """
    record = {
        "product": product,
        "phases_total": len(PHASES),
        "phases_passed": sum(r.evaluation.passed for r in results),
        "gates": [r.phase_id for r in results if r.gated],
        "cost_usd": round(sum(r.cost_usd for r in results), 5),
        "duration_ms": sum(r.duration_ms for r in results),
        "library": library.summary(),
        "results": [r.to_dict() for r in results],
    }
    record["partial"] = partial
    name = "build.partial.json" if partial else "build.json"
    (workspace / name).write_text(json.dumps(record, indent=2))
    return record
