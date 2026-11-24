"""Draft the plan for one implementation run, for a person to accept.

Nothing is built without an accepted plan. The plan is drafted from the
task's intent and the same contract the build will be given - the withheld
one when the rules are withheld - so it can never reveal what is held back.
"""

from __future__ import annotations

from aml.build.brief import read_prd
from aml.build.orchestrator import withheld_contract

INSTRUCTION = """You are planning one implementation run in an AI engineering factory.
Read the task intent and the integration contract below, then write the plan in
markdown with exactly these four sections and nothing else:

## What will be built
## Files that change
## How it will be proven
## Risks

Keep it under 200 words. Do not write code. Do not invent rules or thresholds
the contract does not state; where the contract is silent, say that the
acceptance suite will decide."""


def plan_prompt(intent: str, withhold_rules: bool) -> str:
    """The planning prompt: instruction, the task's intent, and the contract."""
    contract = withheld_contract() if withhold_rules else read_prd()
    return "\n\n".join([INSTRUCTION, "THE TASK INTENT", intent,
                        "THE INTEGRATION CONTRACT", contract])
