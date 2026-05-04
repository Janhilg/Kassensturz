import logging
import sqlite3
from pathlib import Path

from config import Config
from core.storage_connection import get_connection, now_iso
from core.storage_schema import DENOM_FIELDS
from core.version import DB_SCHEMA_VERSION

logger = logging.getLogger(__name__)

SCHEMA_VERSION = DB_SCHEMA_VERSION


CASH_ACCOUNT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cash_accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL,
    current_balance_cents INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
)
"""

CASH_CONTEXT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cash_contexts (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
"""

CASH_MOVEMENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cash_movements (
    id TEXT PRIMARY KEY,
    context_id TEXT,
    context_label TEXT DEFAULT '',
    effective_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    from_account_id TEXT,
    to_account_id TEXT,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    actor TEXT DEFAULT '',
    reference TEXT DEFAULT '',
    note TEXT DEFAULT '',

    denom_100 INTEGER,
    denom_50 INTEGER,
    denom_20 INTEGER,
    denom_10 INTEGER,
    denom_5 INTEGER,
    denom_2 INTEGER,
    denom_1 INTEGER,
    denom_050 INTEGER,
    denom_020 INTEGER,
    denom_010 INTEGER,
    roll_2 INTEGER,
    roll_1 INTEGER,
    roll_050 INTEGER,

    FOREIGN KEY (context_id) REFERENCES cash_contexts(id),
    FOREIGN KEY (from_account_id) REFERENCES cash_accounts(id),
    FOREIGN KEY (to_account_id) REFERENCES cash_accounts(id)
)
"""

CASH_COUNT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cash_counts (
    id TEXT PRIMARY KEY,
    context_id TEXT,
    context_label TEXT DEFAULT '',
    cash_account_id TEXT NOT NULL,
    counted_at TEXT NOT NULL,
    count_type TEXT NOT NULL,
    counted_by TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    note TEXT DEFAULT '',

    denom_100 INTEGER,
    denom_50 INTEGER,
    denom_20 INTEGER,
    denom_10 INTEGER,
    denom_5 INTEGER,
    denom_2 INTEGER,
    denom_1 INTEGER,
    denom_050 INTEGER,
    denom_020 INTEGER,
    denom_010 INTEGER,
    roll_2 INTEGER,
    roll_1 INTEGER,
    roll_050 INTEGER,

    FOREIGN KEY (context_id) REFERENCES cash_contexts(id),
    FOREIGN KEY (cash_account_id) REFERENCES cash_accounts(id)
)
"""


# ============================================================================
# Schema migrations
# ============================================================================

DENOM_MIGRATION_COLUMNS = {field: f"{field} INTEGER" for field in DENOM_FIELDS}

CASH_ACCOUNT_MIGRATION_COLUMNS = {
    "account_type": (f"account_type TEXT NOT NULL DEFAULT '{Config.ACCOUNT_TYPE_CASH_BOX}'"),
    "current_balance_cents": "current_balance_cents INTEGER NOT NULL DEFAULT 0",
    "is_active": "is_active INTEGER NOT NULL DEFAULT 1",
    "sort_order": "sort_order INTEGER NOT NULL DEFAULT 0",
    "created_at": "created_at TEXT NOT NULL DEFAULT ''",
}

CASH_CONTEXT_MIGRATION_COLUMNS = {
    "label": "label TEXT NOT NULL DEFAULT ''",
    "created_at": "created_at TEXT NOT NULL DEFAULT ''",
    "last_used_at": "last_used_at TEXT NOT NULL DEFAULT ''",
    "is_active": "is_active INTEGER NOT NULL DEFAULT 1",
}

CASH_MOVEMENT_MIGRATION_COLUMNS = {
    "context_id": "context_id TEXT",
    "context_label": "context_label TEXT DEFAULT ''",
    "effective_at": "effective_at TEXT NOT NULL DEFAULT ''",
    "created_at": "created_at TEXT NOT NULL DEFAULT ''",
    "from_account_id": "from_account_id TEXT",
    "to_account_id": "to_account_id TEXT",
    "amount_cents": "amount_cents INTEGER NOT NULL DEFAULT 0",
    "actor": "actor TEXT DEFAULT ''",
    "reference": "reference TEXT DEFAULT ''",
    "note": "note TEXT DEFAULT ''",
    **DENOM_MIGRATION_COLUMNS,
}

CASH_COUNT_MIGRATION_COLUMNS = {
    "context_id": "context_id TEXT",
    "context_label": "context_label TEXT DEFAULT ''",
    "cash_account_id": "cash_account_id TEXT NOT NULL DEFAULT ''",
    "counted_at": "counted_at TEXT NOT NULL DEFAULT ''",
    "count_type": "count_type TEXT NOT NULL DEFAULT ''",
    "counted_by": "counted_by TEXT NOT NULL DEFAULT ''",
    "total_cents": "total_cents INTEGER NOT NULL DEFAULT 0",
    "note": "note TEXT DEFAULT ''",
    **DENOM_MIGRATION_COLUMNS,
}


def _get_schema_version_from_connection(conn) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0] if row else 0)


def _set_schema_version(conn, version: int):
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()

    return {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})")
    }


def _require_columns(conn, table_name: str, required_columns: list[str]):
    missing = [
        column for column in required_columns if column not in _table_columns(conn, table_name)
    ]
    if missing:
        missing_columns = ", ".join(missing)
        raise RuntimeError(
            f"Database table {table_name} is missing required columns: {missing_columns}"
        )


def _add_missing_columns(conn, table_name: str, column_definitions: dict[str, str]):
    existing_columns = _table_columns(conn, table_name)
    for column_name, column_sql in column_definitions.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
            logger.info(
                "Database schema column added | table=%s column=%s",
                table_name,
                column_name,
            )


def _fill_empty_timestamps(conn, table_name: str, columns: list[str]):
    timestamp = now_iso()
    for column_name in columns:
        if column_name in _table_columns(conn, table_name):
            conn.execute(
                f"""
                UPDATE {table_name}
                SET {column_name} = ?
                WHERE {column_name} IS NULL OR {column_name} = ''
                """,
                (timestamp,),
            )


def _ensure_schema_v1(conn):
    conn.execute(CASH_ACCOUNT_TABLE_SQL)
    conn.execute(CASH_CONTEXT_TABLE_SQL)
    conn.execute(CASH_MOVEMENT_TABLE_SQL)
    conn.execute(CASH_COUNT_TABLE_SQL)

    _require_columns(conn, "cash_accounts", ["id", "name"])
    _require_columns(conn, "cash_contexts", ["id"])
    _require_columns(conn, "cash_movements", ["id"])
    _require_columns(conn, "cash_counts", ["id"])

    _add_missing_columns(conn, "cash_accounts", CASH_ACCOUNT_MIGRATION_COLUMNS)
    _add_missing_columns(conn, "cash_contexts", CASH_CONTEXT_MIGRATION_COLUMNS)
    _add_missing_columns(conn, "cash_movements", CASH_MOVEMENT_MIGRATION_COLUMNS)
    _add_missing_columns(conn, "cash_counts", CASH_COUNT_MIGRATION_COLUMNS)

    _fill_empty_timestamps(conn, "cash_accounts", ["created_at"])
    _fill_empty_timestamps(conn, "cash_contexts", ["created_at", "last_used_at"])
    _fill_empty_timestamps(conn, "cash_movements", ["created_at", "effective_at"])
    _fill_empty_timestamps(conn, "cash_counts", ["counted_at"])


SCHEMA_MIGRATIONS = {
    1: _ensure_schema_v1,
}


def migrate_database(conn):
    current_version = _get_schema_version_from_connection(conn)
    if current_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than "
            f"this app supports ({SCHEMA_VERSION})"
        )

    while current_version < SCHEMA_VERSION:
        next_version = current_version + 1
        migration = SCHEMA_MIGRATIONS.get(next_version)
        if migration is None:
            raise RuntimeError(f"No migration registered for schema version {next_version}")

        logger.info(
            "Applying database migration | from=%s to=%s",
            current_version,
            next_version,
        )
        migration(conn)
        _set_schema_version(conn, next_version)
        current_version = next_version

    if current_version == SCHEMA_VERSION:
        _ensure_schema_v1(conn)


def get_schema_version(db_path: Path) -> int:
    with get_connection(db_path) as conn:
        return _get_schema_version_from_connection(conn)


def ensure_db_file(db_path: Path):
    with get_connection(db_path) as conn:
        migrate_database(conn)
        conn.commit()
