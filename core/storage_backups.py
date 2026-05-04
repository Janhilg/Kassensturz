import logging
import shutil
from datetime import datetime
from pathlib import Path

from core.storage_migrations import ensure_db_file

logger = logging.getLogger(__name__)


def create_backup(db_path: Path, backup_dir: Path, max_backups: int = 25):
    ensure_db_file(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"kassensturz_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_file)

    backups = sorted(
        backup_dir.glob("kassensturz_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for old_file in backups[max_backups:]:
        try:
            old_file.unlink()
        except Exception:
            logger.exception("Failed to delete old backup | path=%s", old_file)

    logger.info("Backup created | file=%s", backup_file)

    return backup_file


def list_backups(backup_dir: Path) -> list[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    return sorted(
        backup_dir.glob("kassensturz_backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def restore_backup(db_path: Path, backup_file: Path):
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file, db_path)

    logger.info("Database restored from backup | backup=%s db=%s", backup_file, db_path)
