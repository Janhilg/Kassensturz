from dataclasses import dataclass

from core.cash.sync_result import SyncResult


@dataclass(frozen=True)
class CashMovementResult:
    movement_id: str
    auto_return: dict | None
    sync: SyncResult

    def to_dict(self) -> dict:
        return {
            "movement_id": self.movement_id,
            "auto_return": self.auto_return,
            **self.sync.to_dict(),
        }
