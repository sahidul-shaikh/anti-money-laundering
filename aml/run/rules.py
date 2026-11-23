"""Retrieve the detection rule that applies to one alert.

The thresholds used to be English prose inside the system prompt, transcribed
by a person from a 677-page PDF. Nothing kept them current and nothing said
where they came from.

They are now read out of the Solution Guide by
``scripts/build_rule_catalogue.py`` and retrieved per alert by scenario code.
An alert already carries its scenario, so this is a lookup against a primary
key, not a similarity search - there is no embedding here and nothing to tune.

The practical consequences: the rule text in the prompt now carries the page it
came from, a scenario the catalogue does not cover is reported rather than
silently answered from a model's memory, and the fixed instruction prefix no
longer has to carry thresholds for scenarios this alert is not about.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from aml.core.mode import SYNTHETIC_ONLY

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = (
    ROOT / "tests" / "fixtures" / "rules.json"
    if SYNTHETIC_ONLY
    else ROOT / "library" / "aml" / "rules.json"
)


@dataclass(frozen=True)
class RuleSpec:
    """One rule as the guide defines it, with its provenance."""

    scenario: str
    description: str
    model: str
    model_title: str
    rule_id: str
    rule_name: str
    objective: str
    detection_logic: str
    recurrence: str
    defaults: str
    page: int
    source: str

    def render(self) -> str:
        """The block handed to the model, citing where it came from."""
        lines = [
            "THE DETECTION RULE THIS ALERT FIRED",
            "",
            f"Scenario {self.scenario} - {self.description}",
            f"Model {self.model} [{self.model_title}]",
            f"Rule {self.rule_id} - {self.rule_name}",
            f"Objective: {self.objective}",
            f"Detection logic: {self.detection_logic}",
        ]
        if self.recurrence:
            lines.append(f"Recurrence: {self.recurrence}")
        lines += [
            f"Parameters in force: {self.defaults}",
            "",
            f"Source: {self.source}, page {self.page}. These are the parameters "
            "the detection system actually used. Apply them as written - a "
            "single transaction does not satisfy a recurrence requirement, and "
            "a bound stated as inclusive includes its endpoint.",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario, "model": self.model,
            "rule_id": self.rule_id, "rule_name": self.rule_name,
            "page": self.page, "source": self.source,
            "detection_logic": self.detection_logic,
            "recurrence": self.recurrence, "defaults": self.defaults,
        }


@lru_cache(maxsize=1)
def _catalogue() -> dict:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))


def for_scenario(scenario: str) -> RuleSpec | None:
    """The rule a scenario code implements, or None if it is not catalogued."""
    data = _catalogue()
    entry = data["scenarios"].get(scenario)
    if not entry:
        return None
    model = data["models"].get(entry["model"])
    if not model or not model["rules"]:
        return None

    wanted = entry.get("rule_id")
    rule = next(
        (r for r in model["rules"] if r["rule_id"] == wanted),
        model["rules"][0],
    )
    return RuleSpec(
        scenario=scenario,
        description=entry["description"],
        model=entry["model"],
        model_title=model["title"],
        rule_id=rule["rule_id"],
        rule_name=rule.get("rule_name", ""),
        objective=rule.get("rule_objective", ""),
        detection_logic=rule.get("detection_logic", ""),
        recurrence=rule.get("recurrence", ""),
        defaults=rule.get("default_values", ""),
        page=rule.get("page", 0),
        source=data["source"],
    )


def summary() -> dict:
    """What the catalogue holds, for the console."""
    data = _catalogue()
    return {
        "source": data["source"],
        "pages_in_source": data["pages_in_source"],
        "models": {
            code: {"title": m["title"], "pages": m["pages"],
                   "rules": len(m["rules"])}
            for code, m in data["models"].items()
        },
        "scenarios": data["scenarios"],
        "rules_total": sum(len(m["rules"]) for m in data["models"].values()),
    }
