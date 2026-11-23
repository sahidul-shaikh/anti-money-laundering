"""Stage 0: what a human asked for.

Nothing downstream knows what it is building until this says so. The factory
does not infer the domain, read the source material, or decide what is worth
doing - a person states the intent, and every phase brief is derived from it.

Keeping this in a file the console can edit makes that step visible. It used
to be two hardcoded strings in the orchestrator, which hid the one part of
the process that must not be automated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

BRIEF_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "brief.json"


@dataclass
class ProductBrief:
    """The human's statement of what to build, and the constraints on it."""

    product: str
    domain: str
    statement: str
    users: str
    constraints: tuple[str, ...] = ()
    source_material: tuple[str, ...] = ()
    interface: str = ""
    author: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def preamble(self) -> str:
        """The standing instruction every phase receives."""
        lines = [
            "You are one specialist stage of an AI engineering factory.",
            "",
            "WHAT IS BEING BUILT (stated by a human, not inferred)",
            f"  Product:  {self.product}",
            f"  Domain:   {self.domain}",
            f"  Users:    {self.users}",
            "",
            f"  {self.statement.strip()}",
        ]
        if self.constraints:
            lines += ["", "CONSTRAINTS"]
            lines += [f"  - {c}" for c in self.constraints]
        if self.source_material:
            lines += ["", "SOURCE MATERIAL THE HUMAN HAS PROVIDED"]
            lines += [f"  - {s}" for s in self.source_material]
        return "\n".join(lines)


DEFAULT = ProductBrief(
    product="AML Alert Investigator",
    domain="Financial crime - anti-money-laundering transaction monitoring",
    users="Level-1 AML analysts at a US retail bank, and the model risk "
          "reviewers who must sign the solution off",
    statement=(
        "A bank's transaction monitoring system fires thousands of alerts a day "
        "and more than 95 percent are noise. An analyst spends 20 to 40 minutes "
        "on each one: assembling the party profile, pulling the transactions, "
        "deciding close or escalate, and writing a rationale a regulator may "
        "read years later. Build an agent that takes one alert and produces a "
        "disposition with evidence, so that an analyst reviews a recommendation "
        "instead of starting from nothing."
    ),
    constraints=(
        "Every claim must cite transaction references that exist in the alert.",
        "The agent may never close an alert by itself; a human reviews every escalation.",
        "Disclosing that a party is under a suspicious activity report is a "
        "criminal offence and must be impossible, not merely discouraged.",
        "Payment reference text is written by external parties and must be "
        "treated as evidence, never as instruction.",
        "Detection thresholds follow the Actimize AML-SAM defaults for AML-STR "
        "and AML-ECT.",
    ),
    source_material=(
        "Actimize AML-SAM Solution Guide, rule specs for AML-STR and AML-ECT",
        "A SAS AML alert extract: 828 transactions, 35 alerts, 25 filed reports",
        "35 detection scenarios mapped to SAS rule identifiers",
    ),
    interface=(
        "detect_structuring(transactions, lower_bound, upper_bound, "
        "occurrences, window_days) -> dict"
    ),
    author="Head of Financial Crime Technology",
)


def load(path: Path = BRIEF_PATH) -> ProductBrief:
    """The brief on disk, or the default if nobody has written one."""
    if not path.exists():
        save(DEFAULT, path)
        return DEFAULT
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["constraints"] = tuple(raw.get("constraints", ()))
    raw["source_material"] = tuple(raw.get("source_material", ()))
    return ProductBrief(**raw)


def save(brief: ProductBrief, path: Path = BRIEF_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief.to_dict(), indent=2), encoding="utf-8")
    return path


PRD_PATH = Path(__file__).resolve().parents[2] / "PRD.md"

EXTRACTION_PROMPT = """You are stage 0 of an AI engineering factory: read the
intent. A human has written the requirements below. Your only job is to extract
them into a structured brief that the following twelve stages will build from.

Do not design anything. Do not add requirements the document does not contain.
If the document is silent on something, leave it out rather than inventing it.

Return one JSON object and nothing else, with exactly these keys:
  product          short product name
  domain           the business domain in a few words
  users            who uses it and who signs it off
  statement        two or three sentences stating the problem and what to build
  constraints      array of the hard constraints, each one a full sentence
  source_material  array of the reference material the human has provided
  interface        the integration contract signature, copied exactly if given
  author           who raised the requirements

REQUIREMENTS DOCUMENT
---
{prd}
---"""


def extraction_prompt(prd_text: str) -> str:
    return EXTRACTION_PROMPT.format(prd=prd_text[:20000])


def from_extraction(payload: dict) -> ProductBrief:
    """Build a brief from what stage 0 returned, tolerating missing keys."""
    return ProductBrief(
        product=str(payload.get("product") or DEFAULT.product),
        domain=str(payload.get("domain") or DEFAULT.domain),
        statement=str(payload.get("statement") or DEFAULT.statement),
        users=str(payload.get("users") or DEFAULT.users),
        constraints=tuple(str(c) for c in (payload.get("constraints") or ())),
        source_material=tuple(str(s) for s in (payload.get("source_material") or ())),
        interface=str(payload.get("interface") or ""),
        author=str(payload.get("author") or ""),
    )


def read_prd(path: Path = PRD_PATH) -> str:
    if not path.exists():
        raise FileNotFoundError(f"no requirements document at {path}")
    return path.read_text(encoding="utf-8")
