from dataclasses import dataclass


@dataclass(frozen=True)
class SyncResult:
    imported_counts: int
    imported_movements: int
    uploaded: dict
    backup: str
    duration_seconds: float

    def to_dict(self) -> dict:
        return {
            "imported_counts": self.imported_counts,
            "imported_movements": self.imported_movements,
            "uploaded": self.uploaded,
            "backup": self.backup,
            "duration_seconds": self.duration_seconds,
        }
