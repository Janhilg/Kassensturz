import shutil
import sqlite3
import uuid
from pathlib import Path

SCHEMA = """
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
);
"""

COLUMNS = [
    "id",
    "date",
    "timestamp",
    "event_name",
    "counted_by",
    "cash_sum",
    "event_status",
    "comment",
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


def get_conn(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(db_path) as conn:
        conn.execute(SCHEMA)
        conn.commit()


def new_entry_id():
    return str(uuid.uuid4())


def insert_entry(db_path: Path, entry: dict):
    ensure_db(db_path)

    placeholders = ", ".join("?" for _ in COLUMNS)
    columns_sql = ", ".join(COLUMNS)
    values = [entry.get(col) for col in COLUMNS]

    with get_conn(db_path) as conn:
        conn.execute(
            f"INSERT INTO entries ({columns_sql}) VALUES ({placeholders})",
            values
        )
        conn.commit()


def entry_exists(db_path: Path, entry_id: str) -> bool:
    ensure_db(db_path)
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM entries WHERE id = ? LIMIT 1",
            (entry_id,)
        ).fetchone()
        return row is not None


def merge_imported_entries_append_only(db_path: Path, imported_entries: list[dict]):
    ensure_db(db_path)

    with get_conn(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM entries").fetchall()
        }

        for entry in imported_entries:
            entry_id = entry.get("id")
            if not entry_id or entry_id in existing_ids:
                continue

            values = [entry.get(col) for col in COLUMNS]
            placeholders = ", ".join("?" for _ in COLUMNS)
            columns_sql = ", ".join(COLUMNS)

            conn.execute(
                f"INSERT INTO entries ({columns_sql}) VALUES ({placeholders})",
                values
            )
            existing_ids.add(entry_id)

        conn.commit()


def fetch_all_entries(db_path: Path):
    ensure_db(db_path)
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM entries ORDER BY timestamp ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_db_backup(db_path: Path, backup_dir: Path, max_backups: int = 25):
    backup_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
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