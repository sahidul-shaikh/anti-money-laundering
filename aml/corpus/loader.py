"""Load the real alerts from the supplied SAS AML extract.

Every alert in the extract escalated to a case and filed a form, so each one
loads with label ESCALATE. That is also why synthetic negatives exist.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from aml.corpus.model import (
    ESCALATE,
    REAL,
    Account,
    Alert,
    Party,
    Transaction,
)

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "AntiMoneyLaundering"
    / "Alert_Final_table.xlsx"
)

# Shown on screen and talked through one at a time. Chosen for narrative:
# three alerts that share one case, the alert the models disagree on, a
# hidden-link alert, and a single-transaction organisation alert.
HERO_REAL = {"11368", "11372", "11388", "11379", "11376", "11430", "11441"}


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def load_real_alerts(source: Path = SOURCE) -> list[Alert]:
    """One Alert per ALERT_ID, with its transactions attached."""
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    sheet = workbook["Export Worksheet"]
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()

    header = list(rows[0])
    at = {name: index for index, name in enumerate(header)}

    grouped: dict[str, list[tuple]] = {}
    for row in rows[1:]:
        grouped.setdefault(_clean(row[at["ALERT_ID"]]), []).append(row)

    alerts = []
    for alert_id, group in grouped.items():
        first = group[0]
        party = Party(
            number=_clean(first[at["PARTY_NUMBER"]]),
            name=_clean(first[at["PARTY_NAME"]]),
            type=_clean(first[at["PARTY_TYPE_DESC"]]),
            dob=_clean(first[at["PARTY_DATE_OF_BIRTH"]]),
            occupation=_clean(first[at["OCCUPATION_DESC"]]) or "NOT RECORDED",
            annual_income=float(first[at["ANNUAL_INCOME_AMOUNT"]] or 0),
            city=_clean(first[at["STREET_CITY_NAME"]]),
            state=_clean(first[at["STREET_STATE_CODE"]]),
            country=_clean(first[at["RESIDENCE_COUNTRY_NAME"]]),
        )
        account = Account(
            number=_clean(first[at["ACCOUNT_NUMBER"]]),
            product=_clean(first[at["PRODUCT_NAME"]]),
            opened=_clean(first[at["ACCOUNT_OPEN_DATE"]]),
            status=_clean(first[at["ACCOUNT_STATUS_DESC"]]),
            currency=_clean(first[at["ACCOUNT_CURRENCY_NAME"]]),
            registration=_clean(first[at["ACCOUNT_REGISTRATION_TYPE_DESC"]]),
        )
        transactions = tuple(
            Transaction(
                date=_clean(row[at["DATE_KEY"]]),
                ref=_clean(row[at["TRANSACTION_REFERENCE_NUMBER"]]),
                amount=float(row[at["CURRENCY_AMOUNT"]] or 0),
                direction=_clean(row[at["TRANSACTION_CDI_DESC"]]),
                medium=_clean(row[at["PRIMARY_MEDIUM_DESC"]]),
                country=_clean(row[at["COUNTRY_NAME"]]),
            )
            for row in group
        )
        form = _clean(first[at["FORM_TYPE_CODE"]])
        alerts.append(
            Alert(
                alert_id=alert_id,
                scenario=_clean(first[at["SCENARIO_NAME"]]),
                description=_clean(first[at["ALERT_DESCRIPTION"]]),
                triggered=_clean(first[at["ACTUAL_VALUES_TEXT"]]),
                run_date=_clean(first[at["RUN_DATE"]]),
                party=party,
                account=account,
                transactions=transactions,
                label=ESCALATE,
                provenance=REAL,
                hero=alert_id in HERO_REAL,
                rationale=f"Escalated to case {_clean(first[at['CASE_ID']])} and filed as {form}.",
                case_id=_clean(first[at["CASE_ID"]]),
                form_type=form,
            )
        )
    return sorted(alerts, key=lambda a: a.alert_id)
