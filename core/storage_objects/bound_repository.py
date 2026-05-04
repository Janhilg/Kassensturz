from pathlib import Path


class _BoundRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
