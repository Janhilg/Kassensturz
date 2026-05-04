from pathlib import Path

from core.storage_objects.bound_repository import _BoundRepository


class CashBackupRepository(_BoundRepository):
    def create(self, backup_dir: Path, *, max_backups: int = 25):
        from core import storage

        return storage.create_backup(self.db_path, backup_dir, max_backups=max_backups)

    def list(self, backup_dir: Path) -> list[Path]:
        from core import storage

        return storage.list_backups(backup_dir)

    def restore(self, backup_file: Path):
        from core import storage

        return storage.restore_backup(self.db_path, backup_file)
