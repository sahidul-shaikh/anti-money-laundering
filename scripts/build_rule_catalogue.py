"""Extract the in-scope Actimize rule specifications from the Solution Guide.

Until now the detection thresholds lived as English prose inside the system
prompt, transcribed by a person. Nothing kept them current and nothing cited
where they came from. This reads them out of the source document instead, with
the page each one was taken from, and writes a catalogue the agent retrieves
from by scenario code.

Run: uv run python scripts/build_rule_catalogue.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
GUIDE = next((ROOT / "AntiMoneyLaundering").glob("*Solution*.pdf"))
OUT = ROOT / "library" / "aml" / "rules.json"

# The four detection models the six in-scope scenarios map to.
MODELS = {
    "AML-STR": "Structuring Activity",
    "AML-ECT": "Excessive Cash/Cash-Equivalent Transactions",
    "AML-EBB": "Burst in Beneficiary Activity",
    "AML-MLT": "Customer Identity Discovery",
}

# Which rule each scenario is implemented by. The rule id is what the guide
# calls it; where a model has several, this names the one that applies.
SCENARIOS = {
    "SAS10014": ("AML-STR", "Structured Withdrawals",
                 "AML-STR-CCE-INN-A-D01-DST"),
    "SAS10056": ("AML-STR", "Structured Premiums",
                 "AML-STR-CCE-INN-A-D01-DST"),
    "SAS10016": ("AML-STR", "Structured Deposits Across Locations",
                 "AML-STR-CCE-INN-A-D01-DST"),
    "SAS10050": ("AML-ECT", "Payments Using High-Risk Instruments", None),
    "SAS10602": ("AML-EBB", "Multiple External Remitters, One Internal Beneficiary", None),
    "SAS10012": ("AML-MLT", "Recurring Phone Number", None),
}

# Field labels as they appear in the guide's rule tables, in order. Everything
# between one label and the next belongs to the first.
FIELDS = [
    "Model", "Rule Objective", "Rule Id", "Rule Name (display)", "Alert Level",
    "Alert Type", "Rule Type", "Evaluation Level", "Evaluation Trigger",
    "Detection Logic", "Recurrence", "Scoring Algorithm", "Default Values",
    "Scoring Scales",
]
# What the investigator actually needs. Scoring scales drive Actimize's own
# alert score, not the analyst's disposition, so they are left out.
KEEP = ["rule_id", "rule_name", "rule_objective", "evaluation_level",
        "evaluation_trigger", "detection_logic", "recurrence", "default_values"]

LABEL = re.compile(
    r"^(" + "|".join(re.escape(f) for f in FIELDS) + r")\s+(.*)$", re.M)
HEADER = re.compile(r"^(AML-[A-Z]{2,4})\s*\[([^\]]+)\]", re.M)


def model_pages(reader: PdfReader) -> dict[str, list[int]]:
    """Which pages carry each model's rule tables, by its running header."""
    pages: dict[str, list[int]] = {}
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for match in HEADER.finditer(text):
            if match.group(1) in MODELS:
                pages.setdefault(match.group(1), []).append(index)
    return pages


QUOTES = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "�": "'",
})
# Cross-references to the appendices are navigation, not rule content.
BOILERPLATE = re.compile(
    r"\s*For a list of .*?see\s+Appendix.*$|\s*\[See Section\s.*?\]", re.S)


def clean(value: str) -> str:
    """Collapse the guide's hard-wrapped lines and drop its page furniture."""
    lines = []
    for line in value.splitlines():
        line = line.strip().translate(QUOTES)
        if not line or line.startswith("PRODUCT CONFIDENTIAL"):
            continue
        if line.startswith("Actimize AML Suspicious Activity Monitoring"):
            continue
        if HEADER.match(line):
            continue
        lines.append(line)
    return BOILERPLATE.sub("", " ".join(lines)).strip()


def parse_rules(text: str, page_of: dict[int, int]) -> list[dict]:
    """Every rule table in this model's pages, as field dictionaries."""
    marks = [(m.start(), m.group(1), m.group(2)) for m in LABEL.finditer(text)]
    rules: list[dict] = []
    current: dict = {}
    for i, (start, label, first) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = clean(first + "\n" + text[start + len(label) + len(first):end])
        key = label.lower().replace(" (display)", "").replace(" ", "_")
        if label == "Model" and current.get("rule_id"):
            rules.append(current)
            current = {}
        current[key] = body
        if label == "Rule Id":
            current["_offset"] = start
    if current.get("rule_id"):
        rules.append(current)

    for rule in rules:
        offset = rule.pop("_offset", 0)
        rule["page"] = page_of.get(offset, 0)
    return rules


def build() -> dict:
    reader = PdfReader(str(GUIDE))
    pages = model_pages(reader)
    catalogue: dict = {
        "source": GUIDE.name,
        "pages_in_source": len(reader.pages),
        "models": {},
        "scenarios": {},
    }

    for code, title in MODELS.items():
        found = pages.get(code, [])
        if not found:
            continue
        text, page_of, cursor = "", {}, 0
        for number in found:
            body = (reader.pages[number - 1].extract_text() or "") + "\n"
            for position in range(cursor, cursor + len(body)):
                page_of[position] = number
            text += body
            cursor += len(body)

        rules = [
            {k: v for k, v in rule.items() if k in KEEP or k == "page"}
            for rule in parse_rules(text, page_of)
            if rule.get("rule_id", "").startswith(code)
        ]
        catalogue["models"][code] = {
            "title": title,
            "pages": [found[0], found[-1]],
            "rules": rules,
        }

    for scenario, (model, label, rule_id) in SCENARIOS.items():
        catalogue["scenarios"][scenario] = {
            "description": label, "model": model, "rule_id": rule_id,
        }
    return catalogue


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}")
    for code, model in data["models"].items():
        print(f"  {code}  pages {model['pages'][0]}-{model['pages'][1]}  "
              f"{len(model['rules'])} rules")
