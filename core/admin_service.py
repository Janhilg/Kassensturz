from pathlib import Path

from core.admin_maintenance_service import AdminMaintenanceService

_default_admin_service = AdminMaintenanceService()


def list_backups(backup_dir: Path):
    return _default_admin_service.list_backups(backup_dir)


def human_size(num_bytes: int) -> str:
    return _default_admin_service.human_size(num_bytes)


def get_status_snapshot(
    *,
    db_path: Path,
    backup_dir: Path,
    excel_path: Path,
    text_path: Path,
    config,
):
    return _default_admin_service.get_status_snapshot(
        db_path=db_path,
        backup_dir=backup_dir,
        excel_path=excel_path,
        text_path=text_path,
        config=config,
    )


def rebuild_exports(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
):
    return _default_admin_service.rebuild_exports(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )


def sync_exports_now(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    config,
    base_dir: Path,
    sync_state_file: Path,
):
    return _default_admin_service.sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=config,
        base_dir=base_dir,
        sync_state_file=sync_state_file,
    )


def restore_backup(
    *,
    backup_file: Path,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    config,
    base_dir: Path,
):
    return _default_admin_service.restore_backup(
        backup_file=backup_file,
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=config,
        base_dir=base_dir,
    )


__all__ = [
    "AdminMaintenanceService",
    "get_status_snapshot",
    "human_size",
    "list_backups",
    "rebuild_exports",
    "restore_backup",
    "sync_exports_now",
]
