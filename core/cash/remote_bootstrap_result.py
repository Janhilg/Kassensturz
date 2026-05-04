from dataclasses import dataclass


@dataclass(frozen=True)
class RemoteBootstrapResult:
    imported_counts: int
    imported_movements: int
    source_format: str
    skipped: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "imported_counts": self.imported_counts,
            "imported_movements": self.imported_movements,
            "source_format": self.source_format,
            "skipped": self.skipped,
            "reason": self.reason,
        }
