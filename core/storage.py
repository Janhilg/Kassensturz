import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

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
]

DB_COLUMNS = [
    "id",
    "date",
    "timestamp",
    "event_name",
    "counted_by",
    "cash_sum",
    "event_status",
    "comment",
    *DENOM_FIELDS,
]

ENTRY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    event_name TEXT NOT NULL,
    counted_by TEXT NOT NULL,
    cash_sum REAL NOT NULL,
    event_status TEXT NOT NULL,
    comment TEXT DEFAULT '',
    denom_100 INTEGER,
    denom_50 INTEGER,
    denom_20 INTEGER,
    denom_10 INTEGER,
    denom_5 INTEGER,
    denom_2 INTEGER,
    denom_1 INTEGER,
    denom_050 INTEGER,
    denom_020 INTEGER,
    denom_010 INTEGER
)
"""


def get_connection(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db_file(db_path: Path):
    with get_connection(db_path) as conn:
        conn.execute(ENTRY_TABLE_SQL)
        conn.commit()


def new_entry_id() -> str:
    return str(uuid.uuid4())


def parse_optional_int(raw_value):
    raw_value = str(raw_value).strip()
    if raw_value == "":
        return None
    return int(raw_value)


def get_denomination_values_from_form(form) -> dict:
    return {field: parse_optional_int(form.get(field, "")) for field in DENOM_FIELDS}


def entry_to_db_values(entry: dict) -> list:
    return [entry.get(column) for column in DB_COLUMNS]


def insert_entry(db_path: Path, entry: dict):
    ensure_db_file(db_path)

    placeholders = ", ".join("?" for _ in DB_COLUMNS)
    columns_sql = ", ".join(DB_COLUMNS)

    with get_connection(db_path) as conn:
        conn.execute(
            f"INSERT INTO entries ({columns_sql}) VALUES ({placeholders})",
            entry_to_db_values(entry),
        )
        conn.commit()


def fetch_all_entries(db_path: Path) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM entries ORDER BY timestamp ASC, id ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def merge_imported_entries_append_only(db_path: Path, imported_entries: list[dict]):
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM entries").fetchall()
        }

        placeholders = ", ".join("?" for _ in DB_COLUMNS)
        columns_sql = ", ".join(DB_COLUMNS)

        for entry in imported_entries:
            entry_id = str(entry.get("id", "")).strip()
            if not entry_id or entry_id in existing_ids:
                continue

            conn.execute(
                f"INSERT INTO entries ({columns_sql}) VALUES ({placeholders})",
                entry_to_db_values(entry),
            )
            existing_ids.add(entry_id)

        conn.commit()


def create_backup(db_path: Path, backup_dir: Path, max_backups: int = 25):
    ensure_db_file(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"kassensturz_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_file)

    backups = sorted(
        backup_dir.glob("kassensturz_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for old_file in backups[max_backups:]:
        try:
            old_file.unlink()
        except Exception:
            pass

    return backup_file