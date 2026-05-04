from pathlib import Path

from core.export_utils import CashExportService
from core.nextcloud_sync import NextcloudClient
from core.storage import CashStorage
from core.sync_state import SyncStateStore


class AdminMaintenanceService:
    def __init__(
        self,
        *,
        storage_repo: CashStorage | None = None,
        export_service: CashExportService | None = None,
        nextcloud_client: NextcloudClient | None = None,
        sync_state_store: SyncStateStore | None = None,
    ):
        self.storage = storage_repo or CashStorage()
        self.export_service = export_service or CashExportService()
        self.nextcloud_client = nextcloud_client or NextcloudClient()
        self.sync_state_store = sync_state_store or SyncStateStore()

    def list_backups(self, backup_dir: Path):
        result = []
        for backup in self.storage.list_backups(backup_dir):
            stat = backup.stat()
            result.append(
                {
                    "name": backup.name,
                    "path": backup,
                    "size": stat.st_size,
                    "modified_ts": stat.st_mtime,
                }
            )

        return result

    def human_size(self, num_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if num_bytes < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} TB"

    def get_status_snapshot(
        self,
        *,
        db_path: Path,
        backup_dir: Path,
        excel_path: Path,
        text_path: Path,
        config,
    ):
        self.storage.ensure_db_file(db_path)

        row_counts = {
            "cash_accounts": self.storage.get_row_count(db_path, "cash_accounts"),
            "cash_contexts": self.storage.get_row_count(db_path, "cash_contexts"),
            "cash_movements": self.storage.get_row_count(db_path, "cash_movements"),
            "cash_counts": self.storage.get_row_count(db_path, "cash_counts"),
        }
        backups = self.list_backups(backup_dir)

        return {
            "db_exists": db_path.exists(),
            "db_path": db_path,
            "db_size": db_path.stat().st_size if db_path.exists() else 0,
            "db_size_human": (
                self.human_size(db_path.stat().st_size) if db_path.exists() else "0 B"
            ),
            "excel_exists": excel_path.exists(),
            "excel_path": excel_path,
            "excel_size_human": (
                self.human_size(excel_path.stat().st_size) if excel_path.exists() else "0 B"
            ),
            "text_exists": text_path.exists(),
            "text_path": text_path,
            "text_size_human": (
                self.human_size(text_path.stat().st_size) if text_path.exists() else "0 B"
            ),
            "backup_dir": backup_dir,
            "backup_count": len(backups),
            "row_count": sum(row_counts.values()),
            "row_counts": row_counts,
            "nextcloud_configured": self.nextcloud_client.nextcloud_configured(config),
            "remote_dir": getattr(config, "NEXTCLOUD_REMOTE_DIR", ""),
            "remote_file": getattr(config, "NEXTCLOUD_REMOTE_FILE", ""),
            "backups": [
                {**backup, "size_human": self.human_size(backup["size"])} for backup in backups
            ],
        }

    def rebuild_exports(
        self,
        *,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
    ):
        self.storage.ensure_db_file(db_path)
        self.export_service.export_all(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
        )

    def sync_exports_now(
        self,
        *,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        config,
        base_dir: Path,
        sync_state_file: Path,
    ):
        self.storage.ensure_db_file(db_path)

        self.rebuild_exports(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
        )

        uploaded_total_rows = self.storage.get_row_count(
            db_path, "cash_counts"
        ) + self.storage.get_row_count(db_path, "cash_movements")

        upload_result = {"uploaded": False, "reason": "nextcloud_not_configured"}
        if self.nextcloud_client.nextcloud_configured(config):
            upload_result = {
                "excel": self.nextcloud_client.upload_excel_file_to_nextcloud(
                    config,
                    base_dir,
                    excel_path,
                ),
                "text": self.nextcloud_client.upload_text_file_to_nextcloud(
                    config,
                    base_dir,
                    text_path,
                ),
            }

        self.sync_state_store.update_sync_state(
            sync_state_file,
            {
                "uploaded_total_rows": uploaded_total_rows,
                "uploaded": upload_result,
            },
        )

        return {
            "uploaded_total_rows": uploaded_total_rows,
            "uploaded": upload_result,
        }

    def restore_backup(
        self,
        *,
        backup_file: Path,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        config,
        base_dir: Path,
    ):
        self.storage.restore_backup(db_path=db_path, backup_file=backup_file)

        self.rebuild_exports(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
        )

        if self.nextcloud_client.nextcloud_configured(config):
            self.nextcloud_client.upload_excel_file_to_nextcloud(
                config,
                base_dir,
                excel_path,
            )
            self.nextcloud_client.upload_text_file_to_nextcloud(
                config,
                base_dir,
                text_path,
            )


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
