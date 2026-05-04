import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from core.storage_schema import DENOM_FIELDS, DENOM_VALUE_CENTS


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id() -> str:
    return str(uuid.uuid4())


def get_connection(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def dicts_from_rows(rows) -> list[dict]:
    return [dict(row) for row in rows]


def parse_optional_int(raw_value):
    raw_value = str(raw_value).strip()
    if raw_value == "":
        return None
    return int(raw_value)


def normalize_optional_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_context_label(label) -> str:
    return " ".join(normalize_optional_text(label).split())


def cents_to_eur(cents: int) -> float:
    return cents / 100.0


def eur_to_cents(value) -> int:
    return int(round(float(value) * 100))


def row_values(record: dict, columns: list[str]) -> list:
    return [record.get(column) for column in columns]


def get_denomination_values_from_form(form) -> dict:
    return {field: parse_optional_int(form.get(field, "")) for field in DENOM_FIELDS}


def calculate_total_cents_from_denominations(denoms: dict) -> int:
    total = 0
    for field in DENOM_FIELDS:
        qty = denoms.get(field)
        if qty is None:
            continue
        total += int(qty) * DENOM_VALUE_CENTS[field]
    return total


def denominations_match_total_cents(denoms: dict, total_cents: int) -> bool:
    return calculate_total_cents_from_denominations(denoms) == int(total_cents)


def get_row_count(db_path: Path, table_name: str) -> int:
    from core.storage_migrations import ensure_db_file

    ensure_db_file(db_path)

    allowed_tables = {
        "cash_accounts",
        "cash_contexts",
        "cash_movements",
        "cash_counts",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table name: {table_name}")

    with get_connection(db_path) as conn:
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
