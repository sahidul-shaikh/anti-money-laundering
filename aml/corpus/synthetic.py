"""Synthetic alerts that a competent investigator would close.

The supplied extract contains no closed-without-action alerts, so an agent
could score full marks by escalating everything. These negatives exist to make
the measurement mean something, and they are labelled SYNTHETIC everywhere.

Two design rules keep them honest:

1. They use the same six scenario codes as the real alerts, in roughly the same
   proportions, so the scenario code carries no signal about the answer.
2. Each one is genuinely alert-worthy on its face. A model that pattern-matches
   on "cash below 10,000" or "many transactions" will escalate them. Closing
   them correctly requires applying the recurrence and context rules.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from aml.corpus.model import (
    CLOSE,
    SYNTHETIC,
    Account,
    Alert,
    Party,
    Transaction,
)

SEED = 20261109

# Synthetic references start at 2,000,000,000; real ones are in the 1.039bn
# range, so the two can never collide and any citation is attributable.
_refs = itertools.count(2_000_000_000)

INDIVIDUALS = [
    ("DERRICK HALSTEAD", "1974-03-11", "PROFESSIONAL", 128400, "AUSTIN", "TX"),
    ("PRIYA RAMANATHAN", "1986-09-02", "MANAGEMENT", 141900, "EDISON", "NJ"),
    ("MARCUS OYELARAN", "1991-12-19", "SELF EMPLOYED", 76500, "COLUMBUS", "OH"),
    ("JANET KOWALCZYK", "1958-06-27", "RETIRED", 42300, "ERIE", "PA"),
    ("THOMAS BRENNAN", "1983-01-14", "MILITARY", 68900, "FAYETTEVILLE", "NC"),
    ("ANA LUCIA FERREIRA", "1979-07-30", "SELF EMPLOYED CLERICAL", 59700, "HIALEAH", "FL"),
    ("GREGORY WHITFIELD", "1968-11-05", "OFFICE MANAGER", 87200, "DES MOINES", "IA"),
    ("SIOBHAN DELANEY", "1995-04-22", "ADMINISTRATIVE", 51400, "WORCESTER", "MA"),
    ("RAYMOND OKONKWO", "1971-08-16", "PROFESSIONAL", 163000, "ATLANTA", "GA"),
    ("ELEANOR VOSS", "1962-02-08", "RELIGIOUS", 38600, "SPOKANE", "WA"),
    ("HECTOR SANDOVAL", "1988-10-03", "SELF EMPLOYED", 94100, "TUCSON", "AZ"),
    ("MEGAN ASHWORTH", "2001-05-29", "STUDENT", 18200, "ANN ARBOR", "MI"),
]

ORGANISATIONS = [
    ("CEDAR POINT HARDWARE LLC", "RETAIL TRADE", 740000, "TOLEDO", "OH"),
    ("BRIGHTWATER LAUNDRY SERVICES", "PERSONAL SERVICES", 410000, "MOBILE", "AL"),
    ("NORTHGATE DENTAL ASSOCIATES", "HEALTH SERVICES", 1280000, "BOISE", "ID"),
    ("SUMMIT RIDGE LANDSCAPING INC", "CONSTRUCTION", 530000, "RENO", "NV"),
    ("HARBOUR LANE CAFE GROUP", "FOOD SERVICES", 890000, "PORTLAND", "ME"),
]

PRODUCTS = ["CHECKING ACCT", "SAVINGS ACCT", "MONEY MARKET ACCT"]


@dataclass(frozen=True)
class Archetype:
    """A family of closable alerts, and why closing is the right answer."""

    key: str
    scenario: str
    description: str
    count: int
    organisation: bool
    rationale: str


ARCHETYPES = [
    Archetype(
        "settlement_retained", "SAS10050", "Payments Made Using High-Risk Instruments", 5, False,
        "Lump-sum settlement received by official cheque and retained. The only "
        "outflows are small routine payments, so there is no onward movement and "
        "no layering. Receipt value alone is not suspicion.",
    ),
    Archetype(
        "accumulated_then_purchase", "SAS10050", "Payments Made Using High-Risk Instruments", 4, False,
        "A single large instrument payment funded by salary credits that are visible "
        "in the same transaction list and consistent with declared income. The source "
        "of funds is on the record.",
    ),
    Archetype(
        "supplier_payments_regular", "SAS10050", "Payments Made Using High-Risk Instruments", 4, True,
        "Regular equal-value trade payments by a business, set against revenue credits "
        "visible in the same period. Rhythm and value match the stated line of trade.",
    ),
    Archetype(
        "isolated_near_threshold", "SAS10056", "Structured Premiums", 5, False,
        "One cash deposit below the 10,000 reporting threshold. Structuring requires "
        "recurrence - the rule needs three occurrences in fourteen days and there is "
        "one. A single sub-threshold deposit is not structuring.",
    ),
    Archetype(
        "loan_repayments", "SAS10056", "Structured Premiums", 4, False,
        "Scheduled loan repayments of equal value on the contractual date. Regularity "
        "here is the loan agreement, not structuring.",
    ),
    Archetype(
        "own_account_transfers", "SAS10014", "Structured Withdrawals", 4, False,
        "Round-value transfers between two accounts held by the same party under the "
        "same tax identifier. No third party and no change of beneficial ownership.",
    ),
    Archetype(
        "dormant_benign", "SAS10014", "Structured Withdrawals", 4, False,
        "Dormant account reactivated with low-value activity consistent with the "
        "holder's income. Reactivation alone is not a typology.",
    ),
    Archetype(
        "business_takings", "SAS10016", "Structured Deposits Across Locations", 3, True,
        "Daily cash takings banked at the branches nearest each trading site. Volume "
        "and venue spread are expected for the stated line of business.",
    ),
    Archetype(
        "payroll", "SAS10602", "Multiple external remitters one internal beneficiary", 1, False,
        "Multiple remitters are payroll bureaux for concurrent part-time employment. "
        "Credits match declared income and arrive on salary dates.",
    ),
    Archetype(
        "shared_household_phone", "SAS10012", "Recurring Phone Number", 1, False,
        "The shared telephone number belongs to one household address. Related parties "
        "are family members, which the KYC file already records.",
    ),
]

HERO_ARCHETYPES = {"isolated_near_threshold", "business_takings", "own_account_transfers"}


def _ref() -> str:
    return str(next(_refs))


def _date(rng: random.Random, day: int | None = None) -> str:
    return f"201811{(day or rng.randrange(1, 29)):02d}"


def _txn(date: str, amount: float, direction: str, medium: str) -> Transaction:
    return Transaction(
        date=date,
        ref=_ref(),
        amount=round(amount, 2),
        direction=direction,
        medium=medium,
        country="United States",
    )


def _build(key: str, rng: random.Random) -> tuple[list[Transaction], str]:
    """Transactions and the triggering-values text the scenario would emit."""
    if key == "settlement_retained":
        value = rng.randrange(25_000, 90_000, 500)
        txns = [_txn(_date(rng, 13), value, "CREDIT", "CHECK")]
        for _ in range(rng.randrange(3, 6)):
            txns.append(_txn(_date(rng), rng.randrange(200, 1_800), "DEBIT", "CHECK"))
        return txns, f"Total High-Risk Instrument Deposits =   {value:,}"

    if key == "accumulated_then_purchase":
        salary = rng.randrange(2_900, 5_400, 10)
        txns = []
        for month in (8, 9, 10, 11):
            txns.append(_txn(f"2018{month:02d}26", salary, "CREDIT", "EXTERNAL TRANSFER"))
        spend = round(salary * 3.2, 2)
        txns.append(_txn("20181128", spend, "DEBIT", "MISC"))
        return txns, f"Total High-Risk Instrument Deposits =   {spend:,.0f}"

    if key == "supplier_payments_regular":
        each = rng.randrange(7_000, 14_000, 250)
        txns = []
        for n in range(4):
            txns.append(_txn(_date(rng, 4 + n * 6), each, "DEBIT", "MISC"))
            txns.append(
                _txn(_date(rng, 2 + n * 6), each * rng.uniform(1.3, 1.8), "CREDIT", "EXTERNAL TRANSFER")
            )
        return txns, f"Total High-Risk Instrument Deposits =   {each * 4:,}"

    if key == "isolated_near_threshold":
        value = rng.randrange(9_100, 9_900, 50)
        txns = [_txn(_date(rng, 12), value, "CREDIT", "CASH")]
        for _ in range(rng.randrange(3, 7)):
            txns.append(_txn(_date(rng), rng.randrange(30, 900), "DEBIT", "CHECK"))
        return txns, f"Total Deposits =   {value:,}; Number of Deposits = 1"

    if key == "loan_repayments":
        each = rng.randrange(450, 1_400, 10)
        txns = [_txn(f"2018{m:02d}15", each, "DEBIT", "INTERNAL TRANSFER") for m in (8, 9, 10, 11)]
        return txns, f"Total Deposits =   {each * 4:,}; Number of Deposits = 4"

    if key == "own_account_transfers":
        each = rng.choice([5_000, 10_000, 15_000, 20_000])
        txns = []
        for n in range(rng.randrange(3, 6)):
            day = 3 + n * 5
            txns.append(_txn(_date(rng, day), each, "DEBIT", "INTERNAL TRANSFER"))
            txns.append(_txn(_date(rng, day), each, "CREDIT", "INTERNAL TRANSFER"))
        total = each * (len(txns) // 2)
        return txns, f"Total Withdrawals =   {total:,}; Transaction Count = {len(txns) // 2}"

    if key == "dormant_benign":
        txns = [
            _txn(_date(rng, 18 + n), rng.randrange(40, 620), "DEBIT", "CHECK")
            for n in range(rng.randrange(3, 7))
        ]
        total = sum(t.amount for t in txns)
        return txns, f"Total Withdrawals =   {total:,.0f}; Transaction Count = {len(txns)}"

    if key == "business_takings":
        txns = []
        for day in range(1, 26):
            if day % 7 in (0, 6):
                continue
            txns.append(_txn(_date(rng, day), rng.randrange(1_900, 6_200), "CREDIT", "CASH"))
        total = sum(t.amount for t in txns)
        return txns, f"Total Deposits =   {total:,.0f}; Branch Count = 3; Transaction Count = {len(txns)}"

    if key == "payroll":
        txns = []
        for month in (9, 10, 11):
            for amount in (2_180, 1_640, 890):
                txns.append(_txn(f"2018{month:02d}28", amount, "CREDIT", "EXTERNAL TRANSFER"))
        total = sum(t.amount for t in txns)
        return txns, f"Total Transactions=  {total:,.0f}; Remitter Count=3; Internal Beneficiary Count=1"

    # shared_household_phone
    txns = [_txn(_date(rng), rng.randrange(60, 1_400), "DEBIT", "CHECK") for _ in range(5)]
    return txns, "Phone Number 5094412208 Listed for 3 Parties in 1 State"


def build_negatives() -> list[Alert]:
    """The synthetic closable alerts, deterministic for a fixed seed."""
    rng = random.Random(SEED)
    individuals = list(INDIVIDUALS)
    organisations = list(ORGANISATIONS)
    rng.shuffle(individuals)
    rng.shuffle(organisations)

    alerts: list[Alert] = []
    serial = itertools.count(90001)

    for archetype in ARCHETYPES:
        for instance in range(archetype.count):
            if archetype.organisation:
                name, trade, income, city, state = organisations[
                    len(alerts) % len(organisations)
                ]
                party_type, dob, occupation = "ORGANIZATION", "", trade
            else:
                name, dob, occupation, income, city, state = individuals[
                    len(alerts) % len(individuals)
                ]
                party_type = "INDIVIDUAL"

            number = next(serial)
            party = Party(
                number=f"2{number}",
                name=name,
                type=party_type,
                dob=dob,
                occupation=occupation,
                annual_income=float(income),
                city=city,
                state=state,
                country="UNITED STATES",
            )
            account = Account(
                number=f"02-{number:010d}",
                product=rng.choice(PRODUCTS),
                opened=f"{rng.randrange(2005, 2017)}-0{rng.randrange(1, 9)}-15",
                status="ACTIVE",
                currency="US DOLLAR",
                registration="INDIVIDUAL" if party_type == "INDIVIDUAL" else "CORPORATE",
            )
            transactions, triggered = _build(archetype.key, rng)
            alerts.append(
                Alert(
                    alert_id=f"S{number}",
                    scenario=archetype.scenario,
                    description=archetype.description,
                    triggered=triggered,
                    run_date="30-NOV-18",
                    party=party,
                    account=account,
                    transactions=tuple(transactions),
                    label=CLOSE,
                    provenance=SYNTHETIC,
                    hero=archetype.key in HERO_ARCHETYPES and instance == 0,
                    rationale=archetype.rationale,
                )
            )
    return alerts
