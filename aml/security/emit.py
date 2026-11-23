"""What may leave the system, and in what shape.

Two separate duties. Telemetry must not carry identifiers that turn a metrics
store into a copy of the customer master. And nothing the agent writes may
disclose that a party is under suspicion, because that disclosure is a criminal
offence rather than a policy breach.
"""

from __future__ import annotations

import re

from aml.security.injection import TIPPING_OFF

REDACTION = "[redacted]"

SENSITIVE = [
    (re.compile(r"\b\d{2}-\d{10}\b"), "account"),            # 01-0000000042
    (re.compile(r"\b\d{9}\b"), "tax-id"),                    # 900000042
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "iban"),
    (re.compile(r"\b\d{2}-\d{2}-\d{2}\b"), "sort-code"),
]


class TippingOff(RuntimeError):
    """Blocked: the text would have disclosed a suspicion to its subject."""


def redact(text: str) -> tuple[str, list[str]]:
    """Strip identifiers from anything bound for telemetry."""
    found: list[str] = []
    for pattern, kind in SENSITIVE:
        if pattern.search(text):
            found.append(kind)
            text = pattern.sub(REDACTION, text)
    return text, found


def guard_customer_text(text: str) -> str:
    """Anything customer-facing passes through here, or it does not go out.

    Internal case files are allowed to say a SAR was filed - that is their
    purpose. This gate exists for the surfaces the customer can see.
    """
    match = TIPPING_OFF.search(text)
    if match:
        raise TippingOff(
            f"customer-facing text would disclose {match.group(0)!r}"
        )
    return text


def telemetry_safe(record: dict) -> tuple[dict, list[str]]:
    """Redact every string value in a telemetry record."""
    cleaned: dict = {}
    kinds: list[str] = []
    for key, value in record.items():
        if isinstance(value, str):
            cleaned[key], found = redact(value)
            kinds.extend(found)
        else:
            cleaned[key] = value
    return cleaned, sorted(set(kinds))
