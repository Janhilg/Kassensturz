from dataclasses import dataclass


@dataclass(frozen=True)
class CashCountRequest:
    cash_account_id: str
    counted_by: str
    total_cents: int
    count_type: str
    context_label: str = ""
    note: str = ""
    denominations: dict | None = None
