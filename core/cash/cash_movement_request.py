from dataclasses import dataclass


@dataclass(frozen=True)
class CashMovementRequest:
    amount_cents: int
    from_account_id: str | None = None
    to_account_id: str | None = None
    context_label: str = ""
    actor: str = ""
    reference: str = ""
    note: str = ""
    denominations: dict | None = None
