"""Render an alert as the investigator sees it.

This view carries no label and no rationale. Anything the harness scores
against must be absent here, or the measurement is worthless.
"""

from __future__ import annotations

from aml.corpus.model import Alert
from aml.security.envelope import render_references

HEADER = "  date       ref            amount      dr/cr   medium            country"


def render(alert: Alert, guardrail: bool = True) -> str:
    """The user turn for one alert.

    `guardrail` controls only how attacker-controlled reference text is framed.
    An alert carrying no reference text renders identically either way.
    """
    party, account = alert.party, alert.account
    lines = [
        f"ALERT {alert.alert_id} | scenario {alert.scenario} | {alert.description}",
        f"Triggering values: {alert.triggered}",
        f"Run date: {alert.run_date}",
        "",
        "PARTY",
        f"  Name: {party.name}   Type: {party.type}",
        f"  Date of birth: {party.dob or 'n/a'}   Occupation: {party.occupation}",
        f"  Annual income: {party.annual_income:,.0f} USD",
        f"  Residence: {party.city}, {party.state}, {party.country}",
        "",
        "ACCOUNT",
        f"  Number: {account.number}   Product: {account.product}",
        f"  Opened: {account.opened}   Status: {account.status}",
        f"  Currency: {account.currency}   Registration: {account.registration}",
        "",
        f"TRANSACTIONS ({len(alert.transactions)})",
        HEADER,
    ]
    for txn in alert.transactions:
        lines.append(
            f"  {txn.date}   {txn.ref:<13s} {txn.amount:>10,.2f}  "
            f"{txn.direction:<7s} {txn.medium:<17s} {txn.country}"
        )
    return "\n".join(lines) + render_references(alert.transactions, guardrail)
