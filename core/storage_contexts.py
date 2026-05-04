import logging
from pathlib import Path

from core.storage_connection import (
    dicts_from_rows,
    get_connection,
    new_id,
    normalize_context_label,
    now_iso,
    row_values,
)
from core.storage_migrations import ensure_db_file
from core.storage_schema import CASH_CONTEXT_COLUMNS

logger = logging.getLogger(__name__)


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


def merge_imported_cash_contexts_append_only(
    db_path: Path,
    imported_contexts: list[dict],
):
    ensure_db_file(db_path)

    imported_count = 0
    skipped_count = 0

    with get_connection(db_path) as conn:
        existing_ids = {
            row["id"] for row in conn.execute("SELECT id FROM cash_contexts").fetchall()
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
