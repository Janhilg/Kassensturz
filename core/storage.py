import shutil
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

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


# ============================================================================
# SQL schema
# ============================================================================

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
# Generic helpers
# ============================================================================

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


def ensure_db_file(db_path: Path):
    with get_connection(db_path) as conn:
        conn.execute(CASH_ACCOUNT_TABLE_SQL)
        conn.execute(CASH_CONTEXT_TABLE_SQL)
        conn.execute(CASH_MOVEMENT_TABLE_SQL)
        conn.execute(CASH_COUNT_TABLE_SQL)
        conn.commit()


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

def require_cash_account_by_name(db_path: Path, name: str) -> dict:
    account = fetch_cash_account_by_name(db_path, name)
    if not account:
        raise ValueError(f"Required cash account not found: {name}")
    return account

def fetch_cash_accounts_by_type(
    db_path: Path,
    account_type: str,
    active_only: bool = True,
) -> list[dict]:
    ensure_db_file(db_path)

    query = """
        SELECT *
        FROM cash_accounts
        WHERE account_type = ?
    """

    params = [account_type]

    if active_only:
        query += " AND is_active = 1"

    query += " ORDER BY sort_order ASC, name ASC"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

# ============================================================================
# Denomination helpers
# ============================================================================

def get_denomination_values_from_form(form) -> dict:
    return {
        field: parse_optional_int(form.get(field, ""))
        for field in DENOM_FIELDS
    }


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


# ============================================================================
# Accounts
# ============================================================================

def insert_cash_account(
    db_path: Path,
    name: str,
    account_type: str,
    current_balance_cents: int = 0,
    is_active: int = 1,
    sort_order: int = 0,
    account_id: str | None = None,
) -> str:
    ensure_db_file(db_path)

    account_id = account_id or new_id()
    created_at = now_iso()
    name = normalize_optional_text(name)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cash_accounts (
                id, name, account_type, current_balance_cents, is_active, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                name,
                account_type,
                int(current_balance_cents),
                int(is_active),
                int(sort_order),
                created_at,
            ),
        )
        conn.commit()

    logger.info(
        "Cash account created | id=%s name=%s type=%s balance_cents=%s",
        account_id,
        name,
        account_type,
        current_balance_cents,
    )
    return account_id


def fetch_all_cash_accounts(
    db_path: Path,
    active_only: bool = False,
) -> list[dict]:
    ensure_db_file(db_path)

    sql = "SELECT * FROM cash_accounts"
    params = []

    if active_only:
        sql += " WHERE is_active = 1"

    sql += " ORDER BY sort_order ASC, name ASC"

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return dicts_from_rows(rows)


def fetch_cash_account_by_id(db_path: Path, account_id: str) -> dict | None:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cash_accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_cash_account_by_name(db_path: Path, name: str) -> dict | None:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cash_accounts WHERE name = ?",
            (normalize_optional_text(name),),
        ).fetchone()
        return dict(row) if row else None


def update_cash_account_active_state(
    db_path: Path,
    account_id: str,
    is_active: bool,
):
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE cash_accounts SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, account_id),
        )
        conn.commit()


def _default_account_translation_key(account_id: str) -> str:
    if account_id.startswith("acc_"):
        return f"account_{account_id.removeprefix('acc_')}"

    return account_id


def _repair_default_account_name_if_needed(
    db_path: Path,
    account_id: str,
    expected_name: str,
    current_name: str,
) -> bool:
    if current_name != _default_account_translation_key(account_id):
        return False

    if current_name == expected_name:
        return False

    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE cash_accounts SET name = ? WHERE id = ?",
            (expected_name, account_id),
        )
        conn.commit()

    logger.info(
        "Repaired default cash account name | id=%s old_name=%s new_name=%s",
        account_id,
        current_name,
        expected_name,
    )
    return True


def seed_default_cash_accounts(db_path: Path):
    ensure_db_file(db_path)

    existing_accounts = {
        row["id"]: row
        for row in fetch_all_cash_accounts(db_path, active_only=False)
    }

    created = 0
    repaired = 0
    for account_id, name, account_type, sort_order in Config.DEFAULT_CASH_ACCOUNTS:
        if account_id in existing_accounts:
            if _repair_default_account_name_if_needed(
                db_path=db_path,
                account_id=account_id,
                expected_name=name,
                current_name=existing_accounts[account_id]["name"],
            ):
                repaired += 1
            continue

        insert_cash_account(
            db_path=db_path,
            account_id=account_id,
            name=name,
            account_type=account_type,
            sort_order=sort_order,
        )
        created += 1

    logger.info("Seeded default cash accounts | created=%s repaired=%s", created, repaired)


# ============================================================================
# Contexts
# ============================================================================

def insert_cash_context(
    db_path: Path,
    label: str,
    context_id: str | None = None,
) -> str:
    ensure_db_file(db_path)

    label = normalize_context_label(label)
    if not label:
        raise ValueError("Context label cannot be empty")

    context_id = context_id or new_id()
    created_at = now_iso()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cash_contexts (
                id, label, created_at, last_used_at, is_active
            ) VALUES (?, ?, ?, ?, 1)
            """,
            (context_id, label, created_at, created_at),
        )
        conn.commit()

    logger.info("Cash context created | id=%s label=%s", context_id, label)
    return context_id


def fetch_cash_context_by_id(db_path: Path, context_id: str) -> dict | None:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cash_contexts WHERE id = ?",
            (context_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_recent_cash_contexts(
    db_path: Path,
    limit: int = 20,
) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM cash_contexts
            WHERE is_active = 1
            ORDER BY last_used_at DESC, label ASC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return dicts_from_rows(rows)


def find_latest_cash_context_by_label(
    db_path: Path,
    label: str,
) -> dict | None:
    ensure_db_file(db_path)

    label = normalize_context_label(label)
    if not label:
        return None

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM cash_contexts
            WHERE label = ? AND is_active = 1
            ORDER BY last_used_at DESC, created_at DESC
            LIMIT 1
            """,
            (label,),
        ).fetchone()
        return dict(row) if row else None


def touch_cash_context(
    db_path: Path,
    context_id: str,
    used_at: str | None = None,
):
    ensure_db_file(db_path)

    used_at = used_at or now_iso()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE cash_contexts
            SET last_used_at = ?
            WHERE id = ?
            """,
            (used_at, context_id),
        )
        conn.commit()


def get_or_create_cash_context(
    db_path: Path,
    label: str,
) -> tuple[str | None, str]:
    ensure_db_file(db_path)

    normalized_label = normalize_context_label(label)
    if not normalized_label:
        return None, ""

    existing = find_latest_cash_context_by_label(db_path, normalized_label)
    if existing:
        touch_cash_context(db_path, existing["id"])
        return existing["id"], normalized_label

    context_id = insert_cash_context(db_path, normalized_label)
    return context_id, normalized_label


# ============================================================================
# Movements
# ============================================================================

def build_cash_movement_record(
    amount_cents: int,
    from_account_id: str | None = None,
    to_account_id: str | None = None,
    effective_at: str | None = None,
    actor: str = "",
    reference: str = "",
    note: str = "",
    context_label: str = "",
    context_id: str | None = None,
    movement_id: str | None = None,
    denominations: dict | None = None,
) -> dict:
    denominations = denominations or {}

    record = {
        "id": movement_id or new_id(),
        "context_id": context_id,
        "context_label": normalize_context_label(context_label),
        "effective_at": effective_at or now_iso(),
        "created_at": now_iso(),
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "amount_cents": int(amount_cents),
        "actor": normalize_optional_text(actor),
        "reference": normalize_optional_text(reference),
        "note": normalize_optional_text(note),
    }

    for field in DENOM_FIELDS:
        record[field] = denominations.get(field)

    return record


def insert_cash_movement(db_path: Path, movement: dict) -> str:
    ensure_db_file(db_path)

    movement = dict(movement)
    context_label = movement.get("context_label", "")
    context_id = movement.get("context_id")

    if context_id:
        context = fetch_cash_context_by_id(db_path, context_id)
        if not context:
            raise ValueError(f"Unknown context_id: {context_id}")

        movement["context_id"] = context_id
        movement["context_label"] = context_label or context["label"]
        touch_cash_context(db_path, context_id)
    else:
        resolved_context_id, resolved_label = get_or_create_cash_context(
            db_path,
            context_label,
        )
        movement["context_id"] = resolved_context_id
        movement["context_label"] = resolved_label

    placeholders = ", ".join("?" for _ in CASH_MOVEMENT_COLUMNS)
    columns_sql = ", ".join(CASH_MOVEMENT_COLUMNS)

    with get_connection(db_path) as conn:
        conn.execute(
            f"INSERT INTO cash_movements ({columns_sql}) VALUES ({placeholders})",
            row_values(movement, CASH_MOVEMENT_COLUMNS),
        )
        conn.commit()

    logger.info(
        f"Cash movement inserted | id={movement['id']} amount_cents={movement['amount_cents']} "
        f"from={movement['from_account_id']} to={movement['to_account_id']} "
        f"context={movement['context_label']}"
    )
    return movement["id"]


def create_cash_movement(
    db_path: Path,
    amount_cents: int,
    from_account_id: str | None = None,
    to_account_id: str | None = None,
    effective_at: str | None = None,
    actor: str = "",
    reference: str = "",
    note: str = "",
    context_label: str = "",
    context_id: str | None = None,
    movement_id: str | None = None,
    denominations: dict | None = None,
) -> str:
    movement = build_cash_movement_record(
        amount_cents=amount_cents,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        effective_at=effective_at,
        actor=actor,
        reference=reference,
        note=note,
        context_label=context_label,
        context_id=context_id,
        movement_id=movement_id,
        denominations=denominations,
    )
    return insert_cash_movement(db_path, movement)


def fetch_all_cash_movements(db_path: Path) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                m.*,
                fa.name AS from_account_name,
                ta.name AS to_account_name
            FROM cash_movements m
            LEFT JOIN cash_accounts fa ON fa.id = m.from_account_id
            LEFT JOIN cash_accounts ta ON ta.id = m.to_account_id
            ORDER BY m.effective_at ASC, m.created_at ASC, m.id ASC
            """
        ).fetchall()
        return dicts_from_rows(rows)


def fetch_cash_movements_by_context_id(
    db_path: Path,
    context_id: str,
) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                m.*,
                fa.name AS from_account_name,
                ta.name AS to_account_name
            FROM cash_movements m
            LEFT JOIN cash_accounts fa ON fa.id = m.from_account_id
            LEFT JOIN cash_accounts ta ON ta.id = m.to_account_id
            WHERE m.context_id = ?
            ORDER BY m.effective_at ASC, m.created_at ASC, m.id ASC
            """,
            (context_id,),
        ).fetchall()
        return dicts_from_rows(rows)


def fetch_recent_cash_movements(
    db_path: Path,
    limit: int = 50,
) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                m.*,
                fa.name AS from_account_name,
                ta.name AS to_account_name
            FROM cash_movements m
            LEFT JOIN cash_accounts fa ON fa.id = m.from_account_id
            LEFT JOIN cash_accounts ta ON ta.id = m.to_account_id
            ORDER BY m.effective_at DESC, m.created_at DESC, m.id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return dicts_from_rows(rows)


def merge_imported_cash_movements_append_only(
    db_path: Path,
    imported_movements: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0
    remapped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_movements").fetchall()
        }

        account_name_to_id = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM cash_accounts").fetchall()
        }

        existing_context_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
        }

        placeholders = ", ".join("?" for _ in CASH_MOVEMENT_COLUMNS)
        columns_sql = ", ".join(CASH_MOVEMENT_COLUMNS)

        for movement in imported_movements:
            movement_id = str(movement.get("id", "")).strip()
            if not movement_id or movement_id in existing_ids:
                skipped_count += 1
                continue

            normalized = dict(movement)

            from_name = normalized.get("from_account_name")
            to_name = normalized.get("to_account_name")

            if from_name and from_name in account_name_to_id:
                local_from_id = account_name_to_id[from_name]
                if normalized.get("from_account_id") != local_from_id:
                    normalized["from_account_id"] = local_from_id
                    remapped_count += 1

            if to_name and to_name in account_name_to_id:
                local_to_id = account_name_to_id[to_name]
                if normalized.get("to_account_id") != local_to_id:
                    normalized["to_account_id"] = local_to_id
                    remapped_count += 1

            context_id = normalized.get("context_id")
            if context_id and context_id not in existing_context_ids:
                normalized["context_id"] = None

            try:
                conn.execute(
                    f"INSERT INTO cash_movements ({columns_sql}) VALUES ({placeholders})",
                    row_values(normalized, CASH_MOVEMENT_COLUMNS),
                )
            except sqlite3.IntegrityError:
                logger.exception(
                    f"Failed to import cash movement | id={normalized.get("id")}"
                    f" from_id={normalized.get("from_account_id")}"
                    f" from_name={normalized.get("from_account_name")}"
                    f" to_id={normalized.get("to_account_id")}"
                    f" to_name={normalized.get("to_account_name")}"
                    f" context_id={normalized.get("context_id")}"
                )
                raise

            existing_ids.add(movement_id)
            imported_count += 1

        conn.commit()

    logger.info(
        f"Cash movement merge completed | "
        f"imported={imported_count} "
        f"skipped={skipped_count} "
        f"remapped={remapped_count} "
        f"total_remote={len(imported_movements)}"
    )

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "remapped": remapped_count,
        "total": len(imported_movements),
    }

def merge_imported_cash_contexts_append_only(
    db_path: Path,
    imported_contexts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
        }

        placeholders = ", ".join("?" for _ in CASH_CONTEXT_COLUMNS)
        columns_sql = ", ".join(CASH_CONTEXT_COLUMNS)

        for context in imported_contexts:
            context_id = str(context.get("id", "")).strip()

            if not context_id or context_id in existing_ids:
                skipped_count += 1
                continue

            normalized = dict(context)

            if not normalized.get("label"):
                skipped_count += 1
                continue

            if not normalized.get("created_at"):
                normalized["created_at"] = now_iso()

            if not normalized.get("last_used_at"):
                normalized["last_used_at"] = normalized["created_at"]

            if normalized.get("is_active") is None:
                normalized["is_active"] = 1

            conn.execute(
                f"INSERT INTO cash_contexts ({columns_sql}) VALUES ({placeholders})",
                row_values(normalized, CASH_CONTEXT_COLUMNS),
            )

            existing_ids.add(context_id)
            imported_count += 1

        conn.commit()

    logger.info(
        f"Cash context merge completed | "
        f"imported={imported_count} "
        f"skipped={skipped_count} "
        f"total_remote={len(imported_contexts)}"
    )

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "total": len(imported_contexts),
    }


def merge_imported_cash_accounts_append_only(
    db_path: Path,
    imported_accounts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0
    matched_by_name_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_accounts").fetchall()
        }
        existing_names = {
            row["name"]
            for row in conn.execute("SELECT name FROM cash_accounts").fetchall()
        }

        placeholders = ", ".join("?" for _ in CASH_ACCOUNT_COLUMNS)
        columns_sql = ", ".join(CASH_ACCOUNT_COLUMNS)

        for account in imported_accounts:
            account_id = str(account.get("id", "")).strip()
            account_name = str(account.get("name", "")).strip()

            if not account_id or not account_name:
                skipped_count += 1
                continue

            if account_id in existing_ids:
                skipped_count += 1
                continue

            if account_name in existing_names:
                matched_by_name_count += 1
                skipped_count += 1
                logger.info(
                    "Skipped remote cash account with duplicate name | name=%s remote_id=%s",
                    account_name,
                    account_id,
                )
                continue

            normalized = dict(account)

            # current_balance_cents is local live state; do not trust remote value
            normalized["current_balance_cents"] = 0

            if normalized.get("is_active") is None:
                normalized["is_active"] = 1
            if normalized.get("sort_order") is None:
                normalized["sort_order"] = 0
            if not normalized.get("created_at"):
                normalized["created_at"] = now_iso()

            conn.execute(
                f"INSERT INTO cash_accounts ({columns_sql}) VALUES ({placeholders})",
                row_values(normalized, CASH_ACCOUNT_COLUMNS),
            )
            existing_ids.add(account_id)
            existing_names.add(account_name)
            imported_count += 1

        conn.commit()

    logger.info(
        "Cash account merge completed | imported=%s skipped=%s matched_by_name=%s total_remote=%s",
        imported_count,
        skipped_count,
        matched_by_name_count,
        len(imported_accounts),
    )

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "matched_by_name": matched_by_name_count,
        "total": len(imported_accounts),
    }


def merge_imported_cash_counts_append_only(
    db_path: Path,
    imported_counts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0
    remapped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_counts").fetchall()
        }

        account_name_to_id = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM cash_accounts").fetchall()
        }

        existing_context_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
        }

        placeholders = ", ".join("?" for _ in CASH_COUNT_COLUMNS)
        columns_sql = ", ".join(CASH_COUNT_COLUMNS)

        for count_record in imported_counts:
            count_id = str(count_record.get("id", "")).strip()
            if not count_id or count_id in existing_ids:
                skipped_count += 1
                continue

            normalized = dict(count_record)

            account_name = normalized.get("cash_account_name")
            if account_name and account_name in account_name_to_id:
                local_account_id = account_name_to_id[account_name]
                if normalized.get("cash_account_id") != local_account_id:
                    normalized["cash_account_id"] = local_account_id
                    remapped_count += 1

            context_id = normalized.get("context_id")
            if context_id and context_id not in existing_context_ids:
                normalized["context_id"] = None

            try:
                conn.execute(
                    f"INSERT INTO cash_counts ({columns_sql}) VALUES ({placeholders})",
                    row_values(normalized, CASH_COUNT_COLUMNS),
                )
            except sqlite3.IntegrityError:
                logger.exception(
                    "Failed to import cash count | id=%s cash_account_id=%s cash_account_name=%s context_id=%s",
                    normalized.get("id"),
                    normalized.get("cash_account_id"),
                    normalized.get("cash_account_name"),
                    normalized.get("context_id"),
                )
                raise

            existing_ids.add(count_id)
            imported_count += 1

        conn.commit()

    logger.info(
        "Cash count merge completed | imported=%s skipped=%s remapped=%s total_remote=%s",
        imported_count,
        skipped_count,
        remapped_count,
        len(imported_counts),
    )

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "remapped": remapped_count,
        "total": len(imported_counts),
    }

# ============================================================================
# Counts
# ============================================================================

def build_cash_count_record(
    cash_account_id: str,
    counted_by: str,
    total_cents: int,
    count_type: str,
    counted_at: str | None = None,
    note: str = "",
    context_label: str = "",
    context_id: str | None = None,
    count_id: str | None = None,
    denominations: dict | None = None,
) -> dict:
    denominations = denominations or {}

    record = {
        "id": count_id or new_id(),
        "context_id": context_id,
        "context_label": normalize_context_label(context_label),
        "cash_account_id": cash_account_id,
        "counted_at": counted_at or now_iso(),
        "count_type": count_type,
        "counted_by": normalize_optional_text(counted_by),
        "total_cents": int(total_cents),
        "note": normalize_optional_text(note),
    }

    for field in DENOM_FIELDS:
        record[field] = denominations.get(field)

    return record


def insert_cash_count(db_path: Path, count_record: dict) -> str:
    ensure_db_file(db_path)

    count_record = dict(count_record)
    context_label = count_record.get("context_label", "")
    context_id = count_record.get("context_id")

    if context_id:
        context = fetch_cash_context_by_id(db_path, context_id)
        if not context:
            raise ValueError(f"Unknown context_id: {context_id}")

        count_record["context_id"] = context_id
        count_record["context_label"] = context_label or context["label"]
        touch_cash_context(db_path, context_id)
    else:
        resolved_context_id, resolved_label = get_or_create_cash_context(
            db_path,
            context_label,
        )
        count_record["context_id"] = resolved_context_id
        count_record["context_label"] = resolved_label

    placeholders = ", ".join("?" for _ in CASH_COUNT_COLUMNS)
    columns_sql = ", ".join(CASH_COUNT_COLUMNS)

    with get_connection(db_path) as conn:
        conn.execute(
            f"INSERT INTO cash_counts ({columns_sql}) VALUES ({placeholders})",
            row_values(count_record, CASH_COUNT_COLUMNS),
        )
        conn.commit()

    logger.info(
        "Cash count inserted | id=%s account=%s type=%s total_cents=%s context=%s",
        count_record["id"],
        count_record["cash_account_id"],
        count_record["count_type"],
        count_record["total_cents"],
        count_record["context_label"],
    )

    return count_record["id"]


def create_cash_count(
    db_path: Path,
    cash_account_id: str,
    counted_by: str,
    total_cents: int,
    count_type: str,
    counted_at: str | None = None,
    note: str = "",
    context_label: str = "",
    context_id: str | None = None,
    count_id: str | None = None,
    denominations: dict | None = None,
) -> str:
    record = build_cash_count_record(
        cash_account_id=cash_account_id,
        counted_by=counted_by,
        total_cents=total_cents,
        count_type=count_type,
        counted_at=counted_at,
        note=note,
        context_label=context_label,
        context_id=context_id,
        count_id=count_id,
        denominations=denominations,
    )

    return insert_cash_count(db_path, record)


def fetch_all_cash_counts(db_path: Path) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.*,
                a.name AS cash_account_name
            FROM cash_counts c
            LEFT JOIN cash_accounts a ON a.id = c.cash_account_id
            ORDER BY c.counted_at ASC, c.id ASC
            """
        ).fetchall()
        return dicts_from_rows(rows)


def fetch_cash_counts_by_context_id(
    db_path: Path,
    context_id: str,
) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.*,
                a.name AS cash_account_name
            FROM cash_counts c
            LEFT JOIN cash_accounts a ON a.id = c.cash_account_id
            WHERE c.context_id = ?
            ORDER BY c.counted_at ASC, c.id ASC
            """,
            (context_id,),
        ).fetchall()
        return dicts_from_rows(rows)


def fetch_recent_cash_counts(
    db_path: Path,
    limit: int = 50,
) -> list[dict]:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.*,
                a.name AS cash_account_name
            FROM cash_counts c
            LEFT JOIN cash_accounts a ON a.id = c.cash_account_id
            ORDER BY c.counted_at DESC, c.id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return dicts_from_rows(rows)


def merge_imported_cash_counts_append_only(
    db_path: Path,
    imported_counts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM cash_counts").fetchall()
        }

        placeholders = ", ".join("?" for _ in CASH_COUNT_COLUMNS)
        columns_sql = ", ".join(CASH_COUNT_COLUMNS)

        for count_record in imported_counts:
            count_id = str(count_record.get("id", "")).strip()
            if not count_id or count_id in existing_ids:
                skipped_count += 1
                continue

            conn.execute(
                f"INSERT INTO cash_counts ({columns_sql}) VALUES ({placeholders})",
                row_values(count_record, CASH_COUNT_COLUMNS),
            )
            existing_ids.add(count_id)
            imported_count += 1

        conn.commit()

    logger.info(
        "Cash count merge completed | imported=%s skipped=%s total_remote=%s",
        imported_count,
        skipped_count,
        len(imported_counts),
    )

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "total": len(imported_counts),
    }


# ============================================================================
# Balance helpers
# ============================================================================

def _build_account_id_map_by_name(db_path: Path) -> dict[str, str]:
    accounts = fetch_all_cash_accounts(db_path, active_only=False)
    return {row["name"]: row["id"] for row in accounts}


def set_cash_account_balance_cents(db_path: Path, account_id: str, balance_cents: int):
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE cash_accounts
            SET current_balance_cents = ?
            WHERE id = ?
            """,
            (int(balance_cents), account_id),
        )
        conn.commit()

    logger.info(
        "Cash account balance set | account_id=%s balance_cents=%s",
        account_id,
        balance_cents,
    )


def adjust_cash_account_balance_cents(db_path: Path, account_id: str, delta_cents: int):
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE cash_accounts
            SET current_balance_cents = current_balance_cents + ?
            WHERE id = ?
            """,
            (int(delta_cents), account_id),
        )
        conn.commit()

    logger.info(
        "Cash account balance adjusted | account_id=%s delta_cents=%s",
        account_id,
        delta_cents,
    )

def get_cash_account_balance_cents(db_path: Path, account_id: str) -> int:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        incoming = conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0)
            FROM cash_movements
            WHERE to_account_id = ?
            """,
            (account_id,),
        ).fetchone()[0]

        outgoing = conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0)
            FROM cash_movements
            WHERE from_account_id = ?
            """,
            (account_id,),
        ).fetchone()[0]

    return int(incoming or 0) - int(outgoing or 0)


def fetch_cash_account_balances(db_path: Path) -> list[dict]:
    accounts = fetch_all_cash_accounts(db_path, active_only=False)
    result = []

    for account in accounts:
        balance_cents = int(account.get("current_balance_cents") or 0)
        result.append(
            {
                **account,
                "balance_cents": balance_cents,
                "balance_eur": cents_to_eur(balance_cents),
            }
        )

    return result


def fetch_latest_cash_count_for_account(
    db_path: Path,
    cash_account_id: str,
) -> dict | None:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                c.*,
                a.name AS cash_account_name
            FROM cash_counts c
            LEFT JOIN cash_accounts a ON a.id = c.cash_account_id
            WHERE c.cash_account_id = ?
            ORDER BY c.counted_at DESC, c.id DESC
            LIMIT 1
            """,
            (cash_account_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_cash_account_statement(
    db_path: Path,
    account_id: str,
) -> dict:
    account = fetch_cash_account_by_id(db_path, account_id)
    if not account:
        raise ValueError(f"Unknown cash account: {account_id}")

    balance_cents = get_cash_account_balance_cents(db_path, account_id)
    latest_count = fetch_latest_cash_count_for_account(db_path, account_id)

    with get_connection(db_path) as conn:
        incoming_rows = conn.execute(
            """
            SELECT
                m.*,
                fa.name AS from_account_name,
                ta.name AS to_account_name
            FROM cash_movements m
            LEFT JOIN cash_accounts fa ON fa.id = m.from_account_id
            LEFT JOIN cash_accounts ta ON ta.id = m.to_account_id
            WHERE m.to_account_id = ?
            ORDER BY m.effective_at ASC, m.created_at ASC, m.id ASC
            """,
            (account_id,),
        ).fetchall()

        outgoing_rows = conn.execute(
            """
            SELECT
                m.*,
                fa.name AS from_account_name,
                ta.name AS to_account_name
            FROM cash_movements m
            LEFT JOIN cash_accounts fa ON fa.id = m.from_account_id
            LEFT JOIN cash_accounts ta ON ta.id = m.to_account_id
            WHERE m.from_account_id = ?
            ORDER BY m.effective_at ASC, m.created_at ASC, m.id ASC
            """,
            (account_id,),
        ).fetchall()

    return {
        "account": account,
        "balance_cents": balance_cents,
        "balance_eur": cents_to_eur(balance_cents),
        "latest_count": latest_count,
        "incoming_movements": dicts_from_rows(incoming_rows),
        "outgoing_movements": dicts_from_rows(outgoing_rows),
    }


def get_latest_cash_context_label(db_path: Path) -> str:
    ensure_db_file(db_path)

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT label
            FROM cash_contexts
            WHERE is_active = 1
              AND label != ''
            ORDER BY last_used_at DESC, created_at DESC
            LIMIT 1
            """
        ).fetchone()

    return str(row["label"]).strip() if row and row["label"] else ""

# ============================================================================
# Counts and totals
# ============================================================================

def get_row_count(db_path: Path, table_name: str) -> int:
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


# ============================================================================
# Backup
# ============================================================================

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
            logger.exception("Failed to delete old backup | path=%s", old_file)

    logger.info("Backup created | file=%s", backup_file)

    return backup_file

def list_backups(backup_dir: Path) -> list[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    return sorted(
        backup_dir.glob("kassensturz_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def restore_backup(db_path: Path, backup_file: Path):
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file, db_path)

    logger.info("Database restored from backup | backup=%s db=%s", backup_file, db_path)


class CashStorage:
    DENOM_FIELDS = DENOM_FIELDS
    DENOM_VALUE_CENTS = DENOM_VALUE_CENTS
    CASH_ACCOUNT_COLUMNS = CASH_ACCOUNT_COLUMNS
    CASH_CONTEXT_COLUMNS = CASH_CONTEXT_COLUMNS
    CASH_MOVEMENT_COLUMNS = CASH_MOVEMENT_COLUMNS
    CASH_COUNT_COLUMNS = CASH_COUNT_COLUMNS

    now_iso = staticmethod(now_iso)
    new_id = staticmethod(new_id)
    get_connection = staticmethod(get_connection)
    ensure_db_file = staticmethod(ensure_db_file)
    dicts_from_rows = staticmethod(dicts_from_rows)
    parse_optional_int = staticmethod(parse_optional_int)
    normalize_optional_text = staticmethod(normalize_optional_text)
    normalize_context_label = staticmethod(normalize_context_label)
    cents_to_eur = staticmethod(cents_to_eur)
    eur_to_cents = staticmethod(eur_to_cents)
    row_values = staticmethod(row_values)

    require_cash_account_by_name = staticmethod(require_cash_account_by_name)
    fetch_cash_accounts_by_type = staticmethod(fetch_cash_accounts_by_type)
    insert_cash_account = staticmethod(insert_cash_account)
    fetch_all_cash_accounts = staticmethod(fetch_all_cash_accounts)
    fetch_cash_account_by_id = staticmethod(fetch_cash_account_by_id)
    fetch_cash_account_by_name = staticmethod(fetch_cash_account_by_name)
    update_cash_account_active_state = staticmethod(update_cash_account_active_state)
    seed_default_cash_accounts = staticmethod(seed_default_cash_accounts)

    get_denomination_values_from_form = staticmethod(get_denomination_values_from_form)
    calculate_total_cents_from_denominations = staticmethod(
        calculate_total_cents_from_denominations
    )
    denominations_match_total_cents = staticmethod(denominations_match_total_cents)

    insert_cash_context = staticmethod(insert_cash_context)
    fetch_cash_context_by_id = staticmethod(fetch_cash_context_by_id)
    fetch_recent_cash_contexts = staticmethod(fetch_recent_cash_contexts)
    find_latest_cash_context_by_label = staticmethod(find_latest_cash_context_by_label)
    touch_cash_context = staticmethod(touch_cash_context)
    get_or_create_cash_context = staticmethod(get_or_create_cash_context)
    get_latest_cash_context_label = staticmethod(get_latest_cash_context_label)

    build_cash_movement_record = staticmethod(build_cash_movement_record)
    insert_cash_movement = staticmethod(insert_cash_movement)
    create_cash_movement = staticmethod(create_cash_movement)
    fetch_all_cash_movements = staticmethod(fetch_all_cash_movements)
    fetch_cash_movements_by_context_id = staticmethod(fetch_cash_movements_by_context_id)
    fetch_recent_cash_movements = staticmethod(fetch_recent_cash_movements)
    merge_imported_cash_movements_append_only = staticmethod(
        merge_imported_cash_movements_append_only
    )

    merge_imported_cash_contexts_append_only = staticmethod(
        merge_imported_cash_contexts_append_only
    )
    merge_imported_cash_accounts_append_only = staticmethod(
        merge_imported_cash_accounts_append_only
    )
    merge_imported_cash_counts_append_only = staticmethod(
        merge_imported_cash_counts_append_only
    )

    build_cash_count_record = staticmethod(build_cash_count_record)
    insert_cash_count = staticmethod(insert_cash_count)
    create_cash_count = staticmethod(create_cash_count)
    fetch_all_cash_counts = staticmethod(fetch_all_cash_counts)
    fetch_cash_counts_by_context_id = staticmethod(fetch_cash_counts_by_context_id)
    fetch_recent_cash_counts = staticmethod(fetch_recent_cash_counts)

    set_cash_account_balance_cents = staticmethod(set_cash_account_balance_cents)
    adjust_cash_account_balance_cents = staticmethod(adjust_cash_account_balance_cents)
    get_cash_account_balance_cents = staticmethod(get_cash_account_balance_cents)
    fetch_cash_account_balances = staticmethod(fetch_cash_account_balances)
    fetch_latest_cash_count_for_account = staticmethod(fetch_latest_cash_count_for_account)
    fetch_cash_account_statement = staticmethod(fetch_cash_account_statement)

    get_row_count = staticmethod(get_row_count)
    create_backup = staticmethod(create_backup)
    list_backups = staticmethod(list_backups)
    restore_backup = staticmethod(restore_backup)

