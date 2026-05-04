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
from core.storage_schema import CASH_MOVEMENT_COLUMNS, DENOM_FIELDS

logger = logging.getLogger(__name__)


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
            row["id"] for row in conn.execute("SELECT id FROM cash_movements").fetchall()
        }

        account_name_to_id = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM cash_accounts").fetchall()
        }

        existing_context_ids = {
            row["id"] for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
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
                    "Failed to import cash movement | id=%s from_id=%s from_name=%s "
                    "to_id=%s to_name=%s context_id=%s",
                    normalized.get("id"),
                    normalized.get("from_account_id"),
                    normalized.get("from_account_name"),
                    normalized.get("to_account_id"),
                    normalized.get("to_account_name"),
                    normalized.get("context_id"),
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
