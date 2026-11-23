"""The shape of one AML alert, and the labels the harness scores against."""

from __future__ import annotations

from dataclasses import asdict, dataclass

ESCALATE = "escalate_to_case"
CLOSE = "close_no_further_action"

REAL = "real"
SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class Transaction:
    date: str
    ref: str
    amount: float
    direction: str
    medium: str
    country: str
    # Payment reference / remittance free text. Written by whoever sent the
    # payment, so it is the one field in an alert an attacker controls. The
    # supplied extract carries no remittance data, so this is empty for every
    # real transaction and is populated only by the attack corpus.
    reference_text: str = ""


@dataclass(frozen=True)
class Party:
    number: str
    name: str
    type: str
    dob: str
    occupation: str
    annual_income: float
    city: str
    state: str
    country: str


@dataclass(frozen=True)
class Account:
    number: str
    product: str
    opened: str
    status: str
    currency: str
    registration: str


@dataclass(frozen=True)
class Alert:
    """One alert as the investigator sees it, plus the label it is scored against.

    `provenance` is the honesty spine of the demonstration: REAL alerts come
    from the supplied production extract, SYNTHETIC ones were generated because
    that extract contains no closed-without-action alerts.
    """

    alert_id: str
    scenario: str
    description: str
    triggered: str
    run_date: str
    party: Party
    account: Account
    transactions: tuple[Transaction, ...]
    label: str
    provenance: str
    hero: bool
    rationale: str
    case_id: str | None = None
    form_type: str | None = None

    @property
    def refs(self) -> set[str]:
        """Transaction references a grounded answer is allowed to cite."""
        return {t.ref for t in self.transactions}

    def to_dict(self) -> dict:
        return asdict(self)
