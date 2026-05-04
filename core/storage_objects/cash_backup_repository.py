from pathlib import Path

from core.storage_backups import create_backup, list_backups, restore_backup
from core.storage_objects.bound_repository import _BoundRepository


class CashBackupRepository(_BoundRepository):
    def create(self, backup_dir: Path, *, max_backups: int = 25):
        return create_backup(self.db_path, backup_dir, max_backups=max_backups)

    def list(self, backup_dir: Path) -> list[Path]:
        return list_backups(backup_dir)

    def restore(self, backup_file: Path):
        return restore_backup(self.db_path, backup_file)
