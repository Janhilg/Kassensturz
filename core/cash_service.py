import logging
import time
from pathlib import Path

from core import export_utils
from core import nextcloud_sync
from core import storage
from core import sync_state

logger = logging.getLogger(__name__)


def _validate_movement(
    movement_type: str,
    amount_cents: int,
    from_account_id: str | None,
    to_account_id: str | None,
    denominations: dict | None = None,
):
    if amount_cents <= 0:
        raise ValueError("Amount must be > 0")

    if not from_account_id and not to_account_id:
        raise ValueError("Movement must have at least a source or target account")

    if from_account_id and to_account_id and from_account_id == to_account_id:
        raise ValueError("Source and target account cannot be the same")

    if denominations:
        calc = storage.calculate_total_cents_from_denominations(denominations)
        if calc != amount_cents:
            logger.warning(
                "Movement denomination mismatch | calculated=%s total=%s difference=%s",
                calc,
                amount_cents,
                amount_cents - calc,
            )


def _validate_count(
    total_cents: int,
    denominations: dict | None,
):
    if total_cents < 0:
        raise ValueError("Count total cannot be negative")

    # Optional: log mismatch instead of blocking
    if denominations:
        calc = storage.calculate_total_cents_from_denominations(denominations)
        if calc != total_cents:
            logger.warning(
                "Denomination mismatch | calculated=%s total=%s difference=%s",
                calc,
                total_cents,
                total_cents - calc,
            )

def _run_full_sync_pipeline(
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
):
    start_time = time.time()
    logger.info("Sync pipeline started | db=%s", db_path)

    backup_file = storage.create_backup(db_path, backup_dir)
    logger.info("Backup created | file=%s", backup_file)

    export_utils.export_all(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )
    logger.info(
        "Local export complete | excel=%s text=%s",
        excel_path,
        text_path,
    )

    remote_exists = nextcloud_sync.download_remote_excel_if_exists(
        local_excel_path=excel_path,
        config=config,
    )

    imported_counts = 0
    imported_movements = 0
    remote_count_counts = 0
    remote_count_movements = 0

    if remote_exists:
        logger.info("Remote Excel found, starting import")

        remote_data = export_utils.import_all_from_excel(excel_path)
        remote_count_counts = len(remote_data.get("cash_counts", []))
        remote_count_movements = len(remote_data.get("cash_movements", []))

        logger.info(
            "Remote data loaded | counts=%s movements=%s",
            remote_count_counts,
            remote_count_movements,
        )

        counts_result = storage.merge_imported_cash_counts_append_only(
            db_path=db_path,
            imported_counts=remote_data.get("cash_counts", []),
        )

        movements_result = storage.merge_imported_cash_movements_append_only(
            db_path=db_path,
            imported_movements=remote_data.get("cash_movements", []),
        )

        imported_counts = counts_result["imported"]
        imported_movements = movements_result["imported"]

        logger.info(
            "Merge summary | counts imported=%s skipped=%s | movements imported=%s skipped=%s",
            counts_result["imported"],
            counts_result["skipped"],
            movements_result["imported"],
            movements_result["skipped"],
        )
    else:
        logger.info("No remote Excel found")

    export_utils.export_all(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )
    logger.info("Post-merge export complete")

    upload_result = nextcloud_sync.upload_files(
        excel_path=excel_path,
        text_path=text_path,
        config=config,
    )

    logger.info("Upload complete | result=%s", upload_result)

    sync_state.update_sync_state(
        sync_state_file,
        {
            "imported_counts": imported_counts,
            "imported_movements": imported_movements,
            "uploaded": upload_result,
        },
    )

    duration = round(time.time() - start_time, 2)
    logger.info(
        "Sync finished | duration=%.2fs imported_counts=%s imported_movements=%s remote_counts=%s remote_movements=%s",
        duration,
        imported_counts,
        imported_movements,
        remote_count_counts,
        remote_count_movements,
    )

    return {
        "imported_counts": imported_counts,
        "imported_movements": imported_movements,
        "uploaded": upload_result,
        "backup": str(backup_file),
        "duration_seconds": duration,
    }


def record_cash_count_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
    cash_account_id: str,
    counted_by: str,
    total_cents: int,
    count_type: str,
    context_label: str = "",
    note: str = "",
    denominations: dict | None = None,
):
    logger.info(
        "Recording cash count | account=%s counted_by=%s total_cents=%s type=%s context=%s",
        cash_account_id,
        counted_by,
        total_cents,
        count_type,
        context_label,
    )

    _validate_count(total_cents, denominations)

    if denominations:
        denoms = {k: v for k, v in denominations.items() if v not in (None, 0, "")}
        if denoms:
            logger.debug("Count denominations | %s", denoms)

    count_id = storage.create_cash_count(
        db_path=db_path,
        cash_account_id=cash_account_id,
        counted_by=counted_by,
        total_cents=total_cents,
        count_type=count_type,
        context_label=context_label,
        note=note,
        denominations=denominations,
    )

    logger.info("Cash count saved | id=%s", count_id)

    sync_result = _run_full_sync_pipeline(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )

    return {
        "count_id": count_id,
        **sync_result,
    }


def record_cash_movement_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,

    movement_type: str,
    amount_cents: int,
    from_account_id: str | None = None,
    to_account_id: str | None = None,

    context_label: str = "",
    actor: str = "",
    reference: str = "",
    note: str = "",
    denominations: dict | None = None,
):
    logger.info(
        "Recording cash movement | type=%s amount=%s context=%s",
        movement_type,
        amount_cents,
        context_label,
    )

    _validate_movement(
        movement_type,
        amount_cents,
        from_account_id,
        to_account_id,
        denominations,
    )

    movement_id = storage.create_cash_movement(
        db_path=db_path,
        movement_type=movement_type,
        amount_cents=amount_cents,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        context_label=context_label,
        actor=actor,
        reference=reference,
        note=note,
        denominations=denominations,
    )

    sync_result = _run_full_sync_pipeline(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )

    return {
        "movement_id": movement_id,
        **sync_result,
    }

def rebuild_exports_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
):
    logger.info("Manual rebuild + sync triggered")
    return _run_full_sync_pipeline(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )