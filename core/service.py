from pathlib import Path
import tempfile
import time

from core.storage import (
    ensure_db_file,
    insert_entry,
    merge_imported_entries_append_only,
    create_backup,
    get_row_count
)
from core.export_utils import (
    export_entries_to_excel,
    export_entries_to_text,
    import_entries_from_excel,
)
from core.nextcloud_sync import (
    nextcloud_configured,
    download_remote_excel_to_temp,
    upload_excel_file_to_nextcloud,
    upload_text_file_to_nextcloud,
)
import logging

logger = logging.getLogger(__name__)


# IMPORTANT:
# Remote Excel is treated as append-only.
# Existing entries are never modified, only new IDs are imported.
def append_and_sync(
    *,
    entry: dict,
    db_path,
    backup_dir,
    excel_path,
    text_path,
    config,
    base_dir,
    is_debug,
):
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

    local_before = get_row_count(db_path)
    logger.debug("Row count before merge | local=%s", local_before)

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        remote_excel_file = tmp_dir / "remote.xlsx"

        remote_exists = False
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
            local_after = get_row_count(db_path)
            logger.info(
                "Row count | local_before=%s remote=%s after_merge=%s",
                local_before,
                remote_count,
                local_after,
            )

        create_backup(db_path, backup_dir)
        export_entries_to_excel(db_path, excel_path)
        export_entries_to_text(db_path, text_path)

        entries_after = get_row_count(db_path)
        logger.info(
            "Export row count | excel=%s text=%s",
            entries_after,
            entries_after,
        )
        if local_after != remote_count and remote_count != 0:
            logger.warning(
                "Row count mismatch | local=%s remote=%s",
                local_after,
                remote_count
            )

        excel_size = excel_path.stat().st_size
        text_size = text_path.stat().st_size
        logger.info(
            "Exported files | excel=%s (%s) text=%s (%s)",
            excel_size,
            f"{excel_size / 1024:.1f} KB",
            text_size,
            f"{text_size / 1024:.1f} KB",
        )

        if nextcloud_configured(config):
            start = time.time()
            try:
                upload_excel_file_to_nextcloud(config, base_dir, excel_path)
                upload_text_file_to_nextcloud(config, base_dir, text_path)
                logger.info(
                    "Sync completed | id=%s duration=%.2fs",
                    entry.get("id"),
                    time.time() - start
                )
            except Exception:
                logger.exception("Sync failed | id=%s", entry.get("id"))
            raise


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"