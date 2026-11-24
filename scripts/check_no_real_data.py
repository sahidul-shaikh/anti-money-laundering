"""Refuse a commit that carries real customer data. Run by .githooks/pre-push.

Scans the committed tree (not the working folder) for identifiers taken from
the real alert workbook, and for files that must never be committed. Prints
counts only, never a matched value. Real alert and case IDs are reported but
allowed: on their own they identify nobody.

Usage: uv run python scripts/check_no_real_data.py [<commit>]
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import tarfile
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def main_checkout() -> Path:
    """The primary checkout, even when run from a linked worktree.

    The workbook is git-ignored, so it exists only in the primary checkout. A
    worktree that looked for it under its own root would find nothing and
    wave every push through.
    """
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(common).parent


WORKBOOK = main_checkout() / "AntiMoneyLaundering" / "Alert_Final_table.xlsx"

FORBIDDEN_PATHS = (
    "AntiMoneyLaundering/",
    "artifacts/corpus.json",
    "artifacts/run_baseline.json",
    "artifacts/run_attacks.json",
    "library/aml/rules.json",
)

BLOCKING = {
    "name": ["PARTY_NAME", "ACCOUNT_NAME"],
    "tax_or_id": ["PARTY_TAX_ID", "ACCOUNT_TAX_ID", "PARTY_IDENTIFICATION_ID"],
    "account_or_party_no": ["ACCOUNT_NUMBER", "PARTY_NUMBER"],
    "dob": ["PARTY_DATE_OF_BIRTH"],
    "txn_ref": ["TRANSACTION_REFERENCE_NUMBER"],
}
ALLOWED = {"alert_id": ["ALERT_ID"], "case_id": ["CASE_ID"]}


def forms(category: str, value: object) -> set[str]:
    """The textual forms a workbook value may take in a file."""
    if isinstance(value, (datetime, date)):
        d = value.date() if isinstance(value, datetime) else value
        return {d.isoformat(), d.strftime("%d/%m/%Y"), d.strftime("%m/%d/%Y")}
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = " ".join(str(value).split())
    if len(text) < 4:
        return set()
    found = {text}
    parts = text.split()
    if category == "name" and len(parts) >= 2:
        found |= {f"{parts[-1]}, {' '.join(parts[:-1])}", f"{parts[0]} {parts[-1]}"}
    return found


def patterns() -> dict[str, re.Pattern]:
    """One case-insensitive whole-word pattern per category."""
    sheet = load_workbook(WORKBOOK, read_only=True)["Export Worksheet"]
    rows = sheet.iter_rows(values_only=True)
    header = list(next(rows))
    columns = {**BLOCKING, **ALLOWED}
    values: dict[str, set[str]] = {c: set() for c in columns}
    for row in rows:
        for category, names in columns.items():
            for name in names:
                cell = row[header.index(name)]
                if cell not in (None, ""):
                    values[category] |= forms(category, cell)
    return {
        c: re.compile(r"(?<!\w)(" + "|".join(map(re.escape, sorted(v, key=len, reverse=True))) + r")(?!\w)", re.I)
        for c, v in values.items()
    }


def committed_files(commit: str) -> dict[str, str]:
    """Path to text for every file in the commit's tree."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=ROOT, capture_output=True, check=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        return {
            m.name: tar.extractfile(m).read().decode("utf-8", errors="ignore")
            for m in tar.getmembers() if m.isfile()
        }


def main() -> int:
    commit = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    if not WORKBOOK.exists():
        print("real-data scan: workbook not on this machine, nothing to compare against")
        return 0

    files = committed_files(commit)
    blocked = [p for p in files if p.startswith(FORBIDDEN_PATHS)]
    for path in blocked:
        print(f"  BLOCK  {path}: must never be committed")

    allowed_hits = 0
    compiled = patterns()
    for path, text in sorted(files.items()):
        for category, pattern in compiled.items():
            count = len({m.lower() for m in pattern.findall(text)})
            if count and category in BLOCKING:
                blocked.append(path)
                print(f"  BLOCK  {path}: {count} real {category}")
            elif count:
                allowed_hits += count

    print(f"real-data scan of {commit[:10]}: {len(files)} files, "
          f"{len(set(blocked))} blocked, {allowed_hits} real alert/case IDs allowed")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
