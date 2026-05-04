import logging
import sqlite3
from pathlib import Path

from core.storage_connection import (
    dicts_from_rows,
    get_connection,
    new_id,
    normalize_context_label,
    normalize_optional_text,
    now_iso,
    row_values,
)
from core.storage_contexts import (
    fetch_cash_context_by_id,
    get_or_create_cash_context,
    touch_cash_context,
)
from core.storage_migrations import ensure_db_file
from core.storage_schema import CASH_COUNT_COLUMNS, DENOM_FIELDS

logger = logging.getLogger(__name__)


def merge_imported_cash_counts_append_only(
    db_path: Path,
    imported_counts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0
    remapped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {row["id"] for row in conn.execute("SELECT id FROM cash_counts").fetchall()}

        account_name_to_id = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM cash_accounts").fetchall()
        }

        existing_context_ids = {
            row["id"] for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
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


# ============================================================================
# Balance helpers
# ============================================================================


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
