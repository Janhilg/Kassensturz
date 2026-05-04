from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CashSyncContext:
    db_path: Path
    excel_path: Path
    text_path: Path
    backup_dir: Path
    sync_state_file: Path
    config: Any
