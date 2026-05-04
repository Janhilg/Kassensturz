import logging
from pathlib import Path

from config import Config
from core.storage_connection import (
    cents_to_eur,
    dicts_from_rows,
    get_connection,
    new_id,
    normalize_optional_text,
    now_iso,
    row_values,
)
from core.storage_counts import fetch_latest_cash_count_for_account
from core.storage_migrations import ensure_db_file
from core.storage_schema import CASH_ACCOUNT_COLUMNS

logger = logging.getLogger(__name__)


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
        row["id"]: row for row in fetch_all_cash_accounts(db_path, active_only=False)
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
            row["id"] for row in conn.execute("SELECT id FROM cash_accounts").fetchall()
        }
        existing_names = {
            row["name"] for row in conn.execute("SELECT name FROM cash_accounts").fetchall()
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
