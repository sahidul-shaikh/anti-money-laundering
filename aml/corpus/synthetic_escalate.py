"""Synthetic alerts a competent investigator would escalate.

Used only in synthetic-only mode (CI and fresh clones), where the real extract
is absent and would otherwise leave the corpus with no positives. Each one is
plainly suspicious on its face, so a model that escalates it is not being
tested on subtlety - these exist so the controls can be exercised, not to
measure accuracy. Labelled SYNTHETIC everywhere, like the negatives.
"""

from __future__ import annotations

from dataclasses import dataclass

from aml.corpus.model import ESCALATE, SYNTHETIC, Account, Alert, Party, Transaction
from aml.corpus.synthetic import _txn


@dataclass(frozen=True)
class Case:
    """One escalatable alert and why escalation is the right answer."""

    alert_id: str
    scenario: str
    description: str
    party: tuple
    hero: bool
    rationale: str


CASES = [
    Case(
        "S80001", "SAS10014", "Structured Withdrawals",
        ("CALLUM REDGRAVE", "2000-08-14", "STUDENT", 21000, "LUBBOCK", "TX"), True,
        "Eight cash withdrawals between 9,200 and 9,900 in twelve days, each just "
        "under the reporting threshold, totalling several times declared income.",
    ),
    Case(
        "S80002", "SAS10016", "Structured Deposits Across Locations",
        ("NADIA FERRELL", "1990-02-03", "UNEMPLOYED", 0, "GARY", "IN"), False,
        "Six sub-threshold cash deposits at different branches in five days by a "
        "party with no declared income.",
    ),
    Case(
        "S80003", "SAS10056", "Structured Premiums",
        ("OWEN TALBRIDGE", "1977-05-21", "LABORER", 31000, "BILOXI", "MS"), False,
        "Four cash premium payments of 9,500 within ten days, inconsistent with "
        "declared income and immediately followed by a surrender request.",
    ),
    Case(
        "S80004", "SAS10050", "Payments Made Using High-Risk Instruments",
        ("GLENVIEW AUTO EXPORTS LLC", "", "WHOLESALE TRADE", 120000, "NEWARK", "NJ"), False,
        "Money orders bought in batches below threshold and wired abroad within "
        "two days. Funds pass straight through; nothing is retained.",
    ),
    Case(
        "S80005", "SAS10050", "Payments Made Using High-Risk Instruments",
        ("PEARL ASHCROFT", "1985-11-30", "NOT RECORDED", 0, "CAMDEN", "NJ"), True,
        "A single 48,000 cash purchase of a cashier's cheque by a party with no "
        "recorded occupation or income. Source of funds unexplained.",
    ),
    Case(
        "S80006", "SAS10602", "Multiple external remitters one internal beneficiary",
        ("DESMOND KELLAWAY", "1993-07-09", "SELF EMPLOYED", 24000, "YONKERS", "NY"), False,
        "Nine unrelated remitters credit one account within a week and the total "
        "leaves by international wire the next day. Classic funnel account.",
    ),
    Case(
        "S80007", "SAS10012", "Recurring Phone Number",
        ("DESMOND KELLAWAY", "1993-07-09", "SELF EMPLOYED", 24000, "YONKERS", "NY"), False,
        "Same party as S80006. Phone number shared by six unrelated parties in four "
        "states, each moving similar round sums to the same overseas beneficiary.",
    ),
]


def _transactions(alert_id: str) -> tuple[list[Transaction], str]:
    """Transactions and the triggering-values text, fixed per case."""
    if alert_id == "S80001":
        amounts = [9_400, 9_850, 9_200, 9_700, 9_900, 9_350, 9_600, 9_800]
        txns = [_txn(f"201811{3 + i:02d}", a, "DEBIT", "CASH") for i, a in enumerate(amounts)]
        return txns, f"Total Withdrawals =   {sum(amounts):,}; Transaction Count = 8"
    if alert_id == "S80002":
        amounts = [9_100, 9_650, 9_400, 9_800, 9_300, 9_550]
        txns = [_txn(f"2018110{5 + i // 2}", a, "CREDIT", "CASH") for i, a in enumerate(amounts)]
        return txns, f"Total Deposits =   {sum(amounts):,}; Branch Count = 4; Transaction Count = 6"
    if alert_id == "S80003":
        txns = [_txn(f"201811{2 + 3 * i:02d}", 9_500, "DEBIT", "CASH") for i in range(4)]
        return txns, "Total Deposits =   38,000; Number of Deposits = 4"
    if alert_id == "S80004":
        txns = [_txn(f"201811{10 + i // 3:02d}", 2_900, "DEBIT", "MONEY ORDER") for i in range(9)]
        txns.append(_txn("20181114", 26_000, "DEBIT", "WIRE"))
        return txns, "Total High-Risk Instrument Deposits =   26,100"
    if alert_id == "S80005":
        return [_txn("20181119", 48_000, "DEBIT", "CASH")], "Total High-Risk Instrument Deposits =   48,000"
    if alert_id == "S80006":
        amounts = [3_200, 4_100, 2_750, 3_900, 4_400, 2_600, 3_350, 4_050, 3_800]
        txns = [_txn(f"201811{12 + i % 6:02d}", a, "CREDIT", "EXTERNAL TRANSFER") for i, a in enumerate(amounts)]
        txns.append(_txn("20181119", sum(amounts), "DEBIT", "WIRE"))
        return txns, f"Total Transactions=  {sum(amounts):,}; Remitter Count=9; Internal Beneficiary Count=1"
    txns = [_txn(f"201811{6 + 4 * i:02d}", 7_500, "DEBIT", "WIRE") for i in range(4)]
    return txns, "Phone Number 7755550142 Listed for 6 Parties in 4 States"


def build_escalations() -> list[Alert]:
    """The synthetic escalatable alerts, fixed and deterministic."""
    alerts = []
    party_numbers: dict[str, str] = {}
    for n, case in enumerate(CASES, start=1):
        name, dob, occupation, income, city, state = case.party
        is_org = name.endswith("LLC")
        party_number = party_numbers.setdefault(name, f"28000{n}")
        transactions, triggered = _transactions(case.alert_id)
        alerts.append(
            Alert(
                alert_id=case.alert_id,
                scenario=case.scenario,
                description=case.description,
                triggered=triggered,
                run_date="30-NOV-18",
                party=Party(
                    number=party_number, name=name,
                    type="ORGANIZATION" if is_org else "INDIVIDUAL",
                    dob=dob, occupation=occupation, annual_income=float(income),
                    city=city, state=state, country="UNITED STATES",
                ),
                account=Account(
                    number=f"02-{80000 + n:010d}", product="CHECKING ACCT",
                    opened="2017-03-15", status="ACTIVE", currency="US DOLLAR",
                    registration="CORPORATE" if is_org else "INDIVIDUAL",
                ),
                transactions=tuple(transactions),
                label=ESCALATE,
                provenance=SYNTHETIC,
                hero=case.hero,
                rationale=case.rationale,
            )
        )
    return alerts
