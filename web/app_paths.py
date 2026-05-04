import sys
from dataclasses import dataclass
from pathlib import Path


def default_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def bundled_resource_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()

    return Path(__file__).resolve().parent.parent


@dataclass
class AppPaths:
    base_dir: Path
    data_dir: Path
    backup_dir: Path
    db_file: Path
    excel_export_file: Path
    text_export_file: Path
    sync_state_file: Path

    @classmethod
    def from_config(cls, config, base_dir: Path):
        data_dir = base_dir / "data" / config.MODE
        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            backup_dir=data_dir / "backups",
            db_file=data_dir / "kassensturz.db",
            excel_export_file=data_dir / "kassensturz_data.xlsx",
            text_export_file=data_dir / "kassensturz_data.txt",
            sync_state_file=data_dir / "sync_state.json",
        )

    @classmethod
    def from_files(
        cls,
        *,
        base_dir: Path,
        db_file: Path,
        excel_export_file: Path,
        text_export_file: Path,
        backup_dir: Path,
        sync_state_file: Path,
    ):
        return cls(
            base_dir=base_dir,
            data_dir=db_file.parent,
            backup_dir=backup_dir,
            db_file=db_file,
            excel_export_file=excel_export_file,
            text_export_file=text_export_file,
            sync_state_file=sync_state_file,
        )
