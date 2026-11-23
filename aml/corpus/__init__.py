"""The alert corpus: real alerts from the extract, plus synthetic negatives."""

from __future__ import annotations

import json
from pathlib import Path

from aml.core.mode import SYNTHETIC_ONLY
from aml.corpus.loader import load_real_alerts
from aml.corpus.model import (
    CLOSE,
    ESCALATE,
    REAL,
    SYNTHETIC,
    Account,
    Alert,
    Party,
    Transaction,
)
from aml.corpus.render import render
from aml.corpus.synthetic import build_negatives
from aml.corpus.synthetic_escalate import build_escalations

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"


def build_corpus(refresh: bool = False) -> list[Alert]:
    """Every alert the harness scores against, positives first.

    Reads the cached snapshot when there is one. The source workbook is an
    Excel file that anything on the machine can hold a lock on, and a demo
    that dies because a spreadsheet is open is not a demo. Pass refresh=True
    to rebuild from the workbook. In synthetic-only mode the workbook and
    the cache are never touched.
    """
    if SYNTHETIC_ONLY:
        return build_escalations() + build_negatives()
    cache = ARTIFACTS / "corpus.json"
    if not refresh and cache.exists():
        return read_corpus(cache)
    corpus = load_real_alerts() + build_negatives()
    write_corpus(corpus)
    return corpus


def read_corpus(path: Path) -> list[Alert]:
    """Rebuild the corpus from its snapshot."""
    payload = json.loads(path.read_text())
    return [
        Alert(
            **{
                **record,
                "party": Party(**record["party"]),
                "account": Account(**record["account"]),
                "transactions": tuple(
                    Transaction(**t) for t in record["transactions"]
                ),
            }
        )
        for record in payload["alerts"]
    ]


def summarise(corpus: list[Alert]) -> dict:
    return {
        "total": len(corpus),
        "escalate": sum(a.label == ESCALATE for a in corpus),
        "close": sum(a.label == CLOSE for a in corpus),
        "real": sum(a.provenance == REAL for a in corpus),
        "synthetic": sum(a.provenance == SYNTHETIC for a in corpus),
        "hero": sum(a.hero for a in corpus),
        "transactions": sum(len(a.transactions) for a in corpus),
        "scenarios": sorted({a.scenario for a in corpus}),
    }


def write_corpus(corpus: list[Alert] | None = None) -> Path:
    """Persist the corpus so the console and the checks read one source."""
    corpus = corpus or build_corpus()
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / "corpus.json"
    path.write_text(
        json.dumps(
            {"summary": summarise(corpus), "alerts": [a.to_dict() for a in corpus]},
            indent=2,
        )
    )
    return path


__all__ = [
    "build_corpus",
    "read_corpus",
    "summarise",
    "write_corpus",
    "render",
    "Alert",
]
