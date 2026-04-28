from pathlib import Path

from core.export_utils import export_entries_to_excel, export_entries_to_text
from core.nextcloud_sync import (
    nextcloud_configured,
    upload_excel_file_to_nextcloud,
    upload_text_file_to_nextcloud,
)
from core.storage import ensure_db_file, fetch_all_entries


def list_backups(backup_dir: Path):
    backup_dir.mkdir(parents=True, exist_ok=True)

    backups = sorted(
        backup_dir.glob("kassensturz_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    result = []
    for backup in backups:
        stat = backup.stat()
        result.append({
            "name": backup.name,
            "path": backup,
            "size": stat.st_size,
            "modified_ts": stat.st_mtime,
        })

    return result


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def get_status_snapshot(
    *,
    db_path: Path,
    backup_dir: Path,
    excel_path: Path,
    text_path: Path,
    config,
):
    ensure_db_file(db_path)

    row_count = len(fetch_all_entries(db_path))
    backups = list_backups(backup_dir)

    return {
        "db_exists": db_path.exists(),
        "db_path": db_path,
        "db_size": db_path.stat().st_size if db_path.exists() else 0,
        "db_size_human": human_size(db_path.stat().st_size) if db_path.exists() else "0 B",
        "excel_exists": excel_path.exists(),
        "excel_path": excel_path,
        "excel_size": excel_path.stat().st_size if excel_path.exists() else 0,
        "excel_size_human": human_size(excel_path.stat().st_size) if excel_path.exists() else "0 B",
        "text_exists": text_path.exists(),
        "text_path": text_path,
        "text_size": text_path.stat().st_size if text_path.exists() else 0,
        "text_size_human": human_size(text_path.stat().st_size) if text_path.exists() else "0 B",
        "backup_dir": backup_dir,
        "backup_count": len(backups),
        "row_count": row_count,
        "nextcloud_configured": nextcloud_configured(config),
        "remote_dir": getattr(config, "NEXTCLOUD_REMOTE_DIR", ""),
        "remote_file": getattr(config, "NEXTCLOUD_REMOTE_FILE", ""),
        "backups": [
            {
                **backup,
                "size_human": human_size(backup["size"]),
            }
            for backup in backups
        ],
    }


def rebuild_exports(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
):
    ensure_db_file(db_path)
    export_entries_to_excel(db_path, excel_path)
    export_entries_to_text(db_path, text_path)


def sync_exports_now(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    config,
    base_dir: Path,
):
    rebuild_exports(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )

    if nextcloud_configured(config):
        upload_excel_file_to_nextcloud(config, base_dir, excel_path)
        upload_text_file_to_nextcloud(config, base_dir, text_path)


def restore_backup(
    *,
    backup_file: Path,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    config,
    base_dir: Path,
):
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup not found: {backup_file}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(backup_file.read_bytes())

    ensure_db_file(db_path)

    rebuild_exports(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )

    if nextcloud_configured(config):
        upload_excel_file_to_nextcloud(config, base_dir, excel_path)
        upload_text_file_to_nextcloud(config, base_dir, text_path)