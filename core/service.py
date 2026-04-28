from pathlib import Path
import tempfile

from core.storage import (
    ensure_db_file,
    insert_entry,
    merge_imported_entries_append_only,
    create_backup,
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

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        remote_excel_file = tmp_dir / "remote.xlsx"

        remote_exists = False
        if nextcloud_configured(config) and not is_debug:
            remote_exists = download_remote_excel_to_temp(config, base_dir, remote_excel_file)

        if remote_exists:
            imported_entries = import_entries_from_excel(remote_excel_file)
            merge_imported_entries_append_only(db_path, imported_entries)

        create_backup(db_path, backup_dir)
        export_entries_to_excel(db_path, excel_path)
        export_entries_to_text(db_path, text_path)

        if nextcloud_configured(config):
            upload_excel_file_to_nextcloud(config, base_dir, excel_path)
            upload_text_file_to_nextcloud(config, base_dir, text_path)