"""The twelve phases, and what each one has to produce to pass.

A phase is a brief, the artifacts it may read, and the markers its output must
contain. The markers are not decoration: the evaluator looks for them, and a
phase that omits one does not pass. Deleting a required section from an
artifact is enough to stop the build.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    name: str
    produces: str
    brief: str
    markers: tuple[str, ...]          # must appear as a heading
    tokens: tuple[str, ...] = ()      # must appear somewhere in the text
    kind: str = "document"            # document | code
    verify_with: tuple[str, ...] = () # acceptance tests a code phase must pass
    depends_on: tuple[str, ...] = ()
    gate: bool = False
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    assets: tuple[str, ...] = field(default=())


PHASES: list[PhaseSpec] = [
    PhaseSpec(
        "contract", "Value contract", "contract.md",
        "Write the value contract for the product described above. State the measured "
        "baseline cost per unit of work, the target, the quality floor below which it "
        "must not be deployed, and the telemetry that will prove realisation. Use the "
        "numbers the brief gives you and be specific.",
        ("BASELINE", "TARGET", "QUALITY FLOOR", "TELEMETRY"),
        gate=True,
        skills=("value-contract",),
        assets=("value-contract-template",),
    ),
    PhaseSpec(
        "spec", "Specification and threat model", "spec.md",
        "Write the specification for the product. Include numbered, testable acceptance "
        "criteria (AC-1 onward). Include a THREAT MODEL section enumerating threats "
        "T-1 onward, covering at minimum every constraint in the brief that concerns "
        "an adversary or a regulator. The threat model is written now, before any "
        "code exists.",
        ("ACCEPTANCE CRITERIA", "THREAT MODEL"),
        tokens=("AC-1", "T-1"),
        depends_on=("contract",),
        gate=True,
        skills=("specification", "threat-modelling"),
        assets=("acceptance-criteria-pattern", "aml-threat-library"),
    ),
    PhaseSpec(
        "architecture", "Architecture", "arch.md",
        "Design the architecture: components, the data flow from input to decision, "
        "trust boundaries, and where each control from the threat model sits. Mark "
        "the boundary across which untrusted external text crosses.",
        ("COMPONENTS", "DATA FLOW", "TRUST BOUNDAR"),
        depends_on=("spec",),
        skills=("architecture",),
        assets=("trust-boundary-pattern",),
    ),
    PhaseSpec(
        "agent_design", "Agent graph and loop", "agent.md",
        "Design the agent itself: the loop (goal, act, verify, iterate), the nodes "
        "and edges of the graph, the shared state between them, and every point at "
        "which a human gate sits. State the stopping condition.",
        ("LOOP", "NODES", "SHARED STATE", "HUMAN GATE"),
        depends_on=("architecture",),
        skills=("agent-design",),
        assets=("agent-loop-pattern", "graph-gate-pattern"),
    ),
    PhaseSpec(
        "context", "Context design", "context.md",
        "Specify exactly what context the agent receives for one unit of work, where "
        "each field comes from, and what is deliberately withheld. Identify which "
        "fields are attacker-controlled and state how they are framed in the prompt.",
        ("CONTEXT SOURCES", "WITHHELD", "ATTACKER-CONTROLLED"),
        depends_on=("agent_design",),
        skills=("context-engineering",),
        assets=("untrusted-data-envelope",),
    ),
    PhaseSpec(
        "development", "Implementation", "src/detector.py",
        "Implement the detection rule described in the requirements, to the "
        "integration contract exactly as written there. Read the parameter "
        "defaults, the boundary conditions, the direction filter, the window "
        "semantics and the output keys from the requirements - every one of them "
        "is specified and every one is tested.\n"
        "Write two files. Return each as a FILE: line followed by a fenced python "
        "block, and nothing else:\n"
        "### FILE: src/detector.py\n"
        "the module, with a docstring and no dependencies outside the standard "
        "library\n"
        "### FILE: tests/test_detector.py\n"
        "your own pytest tests for it, which must import from detector directly.\n"
        "An independent acceptance suite you have not seen will decide whether "
        "this passes.",
        markers=(),
        kind="code",
        verify_with=("checks/acceptance/test_detector_contract.py",),
        depends_on=("context",),
        skills=("implementation",),
        assets=("verdict-schema", "parse-and-grade"),
    ),
    PhaseSpec(
        "evaluation", "Evaluation design", "evaluation.md",
        "Design the evaluation. Define the families of test: correctness against "
        "known outcomes, groundedness of cited evidence, robustness against the "
        "threats in the threat model, and cost. For each family state how it is "
        "measured and what the pass threshold is. State how run-to-run variance is "
        "separated from a real change.",
        ("EVAL FAMILIES", "GROUNDEDNESS", "PASS THRESHOLD", "VARIANCE"),
        depends_on=("development",),
        skills=("evaluation-design",),
        assets=("eval-families", "paired-sign-test"),
    ),
    PhaseSpec(
        "code_review", "Code review", "code_review.md",
        "Review the implementation and evaluation designs as a senior engineer "
        "would. List findings with a severity and a specific remedy. Say plainly "
        "what you would block on.",
        ("FINDINGS", "SEVERITY", "BLOCKING"),
        depends_on=("development", "evaluation"),
        skills=("code-review",),
        assets=("review-checklist",),
    ),
    PhaseSpec(
        "security_review", "Security review", "security_review.md",
        "Verify every threat in the threat model against the architecture and "
        "implementation. For each threat state the control, whether it is "
        "implemented, and the residual risk. List the adversarial probes that must "
        "run before release.",
        ("THREAT COVERAGE", "RESIDUAL RISK", "PROBES"),
        depends_on=("context", "spec"),
        skills=("security-review",),
        assets=("probe-catalogue", "ungrantable-scopes"),
    ),
    PhaseSpec(
        "model_risk", "Model risk documentation", "model_risk.md",
        "Write the model risk documentation a reviewer under the governing model-risk "
        "standard would require: "
        "intended use and limitations, data lineage, performance measurement, "
        "ongoing monitoring, and the conditions under which the model must be "
        "withdrawn from use.",
        ("INTENDED USE", "LIMITATIONS", "MONITORING", "WITHDRAWAL"),
        depends_on=("evaluation", "security_review", "code_review"),
        gate=True,
        skills=("model-risk",),
        assets=("sr11-7-template",),
    ),
    PhaseSpec(
        "functional_test", "Functional test", "functional_test.md",
        "Write the functional test report. Trace every acceptance criterion from the "
        "specification to the test that covers it and state the result. Mark any "
        "criterion that is not covered.",
        ("ACCEPTANCE TRACE", "RESULT"),
        tokens=("AC-1",),
        depends_on=("model_risk",),
        skills=("functional-test",),
        assets=("acceptance-trace",),
    ),
    PhaseSpec(
        "deployment", "Deployment and runbook", "deployment.md",
        "Write the deployment runbook: the telemetry that must be live before "
        "release, the rollback trigger and procedure, the on-call runbook for a "
        "degraded agent, and the review cadence.",
        ("TELEMETRY CONTRACT", "ROLLBACK", "RUNBOOK", "CADENCE"),
        depends_on=("functional_test",),
        gate=True,
        skills=("deployment",),
        assets=("telemetry-contract", "rollback-procedure"),
    ),
]

BY_ID = {p.phase_id: p for p in PHASES}
GATES = tuple(p.phase_id for p in PHASES if p.gate)


def order() -> list[PhaseSpec]:
    """Topological order. Raises if the dependencies do not form a DAG."""
    done: list[PhaseSpec] = []
    seen: set[str] = set()
    remaining = list(PHASES)
    while remaining:
        ready = [p for p in remaining if set(p.depends_on) <= seen]
        if not ready:
            raise ValueError(
                "phase dependencies are cyclic: "
                + ", ".join(p.phase_id for p in remaining)
            )
        for phase in ready:
            done.append(phase)
            seen.add(phase.phase_id)
            remaining.remove(phase)
    return done
