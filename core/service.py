import logging
import time
from pathlib import Path
import tempfile

from core.export_utils import (
    export_entries_to_excel,
    export_entries_to_text,
    import_entries_from_excel,
)
from core.nextcloud_sync import (
    download_remote_excel_to_temp,
    nextcloud_configured,
    upload_excel_file_to_nextcloud,
    upload_text_file_to_nextcloud,
)
from core.storage import (
    create_backup,
    ensure_db_file,
    get_row_count,
    insert_entry,
    merge_imported_entries_append_only,
)
from core.sync_state import load_sync_state, save_sync_state

logger = logging.getLogger(__name__)


def append_and_sync(
    *,
    entry: dict,
    db_path: Path,
    backup_dir: Path,
    excel_path: Path,
    text_path: Path,
    config,
    base_dir: Path,
    is_debug: bool,
    sync_state_file: Path,
):
    start_time = time.time()

    ensure_db_file(db_path)
    insert_entry(db_path, entry)

    logger.info(
        "Submission saved | id=%s event=%s counted_by=%s cash_sum=%s status=%s",
        entry.get("id"),
        entry.get("event_name"),
        entry.get("counted_by"),
        entry.get("cash_sum"),
        entry.get("event_status"),
    )

    denoms = {k: v for k, v in entry.items() if k.startswith("denom_") and v is not None}
    if denoms:
        logger.debug("Denominations | id=%s %s", entry.get("id"), denoms)

    sync_state = load_sync_state(sync_state_file)
    last_uploaded_row_count = int(sync_state.get("last_uploaded_row_count", 0))

    local_before_merge = get_row_count(db_path)
    remote_count = 0
    remote_exists = False
    merge_result = {
        "imported": 0,
        "skipped": 0,
        "total": 0,
    }

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        remote_excel_file = tmp_dir / "remote.xlsx"

        if nextcloud_configured(config) and not is_debug:
            remote_exists = download_remote_excel_to_temp(config, base_dir, remote_excel_file)

        if remote_exists:
            imported_entries = import_entries_from_excel(remote_excel_file)
            remote_count = len(imported_entries)

            logger.info("Remote Excel row count | remote=%s", remote_count)

            merge_result = merge_imported_entries_append_only(db_path, imported_entries)

            logger.info(
                "Merge summary | id=%s imported=%s skipped=%s",
                entry.get("id"),
                merge_result["imported"],
                merge_result["skipped"],
            )

        local_after_merge = get_row_count(db_path)

        logger.info(
            "Row count | last_uploaded=%s local_before_merge=%s remote=%s local_after_merge=%s",
            last_uploaded_row_count,
            local_before_merge,
            remote_count,
            local_after_merge,
        )

        create_backup(db_path, backup_dir)
        export_entries_to_excel(db_path, excel_path)
        export_entries_to_text(db_path, text_path)

        exported_row_count = get_row_count(db_path)

        logger.info(
            "Export row count | excel=%s text=%s",
            exported_row_count,
            exported_row_count,
        )

        new_rows_added_to_shared_dataset = max(0, local_after_merge - last_uploaded_row_count)

        if nextcloud_configured(config):
            try:
                upload_excel_file_to_nextcloud(config, base_dir, excel_path)
                upload_text_file_to_nextcloud(config, base_dir, text_path)

                save_sync_state(
                    sync_state_file,
                    last_uploaded_row_count=exported_row_count,
                )

                duration = time.time() - start_time
                logger.info(
                    "Sync completed | id=%s duration=%.2fs imported=%s skipped=%s new_shared_rows=%s uploaded_total=%s",
                    entry.get("id"),
                    duration,
                    merge_result["imported"],
                    merge_result["skipped"],
                    new_rows_added_to_shared_dataset,
                    exported_row_count,
                )
            except Exception:
                logger.exception("Sync failed | id=%s", entry.get("id"))
                raise

    return {
        "remote_exists": remote_exists,
        "remote_total": remote_count,
        "imported_from_remote": merge_result["imported"],
        "skipped_remote_existing": merge_result["skipped"],
        "uploaded_total_rows": exported_row_count,
        "new_rows_added_to_shared_dataset": new_rows_added_to_shared_dataset,
        "duration_seconds": round(time.time() - start_time, 2),
    }