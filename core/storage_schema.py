DENOM_FIELDS = [
    "denom_100",
    "denom_50",
    "denom_20",
    "denom_10",
    "denom_5",
    "denom_2",
    "denom_1",
    "denom_050",
    "denom_020",
    "denom_010",
    "roll_2",
    "roll_1",
    "roll_050",
]

DENOM_VALUE_CENTS = {
    "denom_100": 10000,
    "denom_50": 5000,
    "denom_20": 2000,
    "denom_10": 1000,
    "denom_5": 500,
    "denom_2": 200,
    "denom_1": 100,
    "denom_050": 50,
    "denom_020": 20,
    "denom_010": 10,
    "roll_2": 5000,
    "roll_1": 2500,
    "roll_050": 2000,
}

CASH_ACCOUNT_COLUMNS = [
    "id",
    "name",
    "account_type",
    "current_balance_cents",
    "is_active",
    "sort_order",
    "created_at",
]

CASH_CONTEXT_COLUMNS = [
    "id",
    "label",
    "created_at",
    "last_used_at",
    "is_active",
]

CASH_MOVEMENT_COLUMNS = [
    "id",
    "context_id",
    "context_label",
    "effective_at",
    "created_at",
    "from_account_id",
    "to_account_id",
    "amount_cents",
    "actor",
    "reference",
    "note",
    *DENOM_FIELDS,
]

CASH_COUNT_COLUMNS = [
    "id",
    "context_id",
    "context_label",
    "cash_account_id",
    "counted_at",
    "count_type",
    "counted_by",
    "total_cents",
    "note",
    *DENOM_FIELDS,
]
