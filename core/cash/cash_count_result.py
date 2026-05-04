from dataclasses import dataclass

from core.cash.sync_result import SyncResult


@dataclass(frozen=True)
class CashCountResult:
    count_id: str
    sync: SyncResult

    def to_dict(self) -> dict:
        return {
            "count_id": self.count_id,
            **self.sync.to_dict(),
        }
