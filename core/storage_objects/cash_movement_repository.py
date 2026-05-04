from core.storage_movements import (
    build_cash_movement_record,
    create_cash_movement,
    fetch_all_cash_movements,
    fetch_cash_movements_by_context_id,
    fetch_recent_cash_movements,
    insert_cash_movement,
    merge_imported_cash_movements_append_only,
)
from core.storage_objects.bound_repository import _BoundRepository


class CashMovementRepository(_BoundRepository):
    def build(self, **kwargs) -> dict:
        return build_cash_movement_record(**kwargs)

    def insert(self, movement: dict) -> str:
        return insert_cash_movement(self.db_path, movement)

    def create(self, **kwargs) -> str:
        return create_cash_movement(self.db_path, **kwargs)

    def all(self) -> list[dict]:
        return fetch_all_cash_movements(self.db_path)

    def by_context_id(self, context_id: str) -> list[dict]:
        return fetch_cash_movements_by_context_id(self.db_path, context_id)

    def recent(self, *, limit: int = 50) -> list[dict]:
        return fetch_recent_cash_movements(self.db_path, limit=limit)

    def merge_imported_append_only(self, imported_movements: list[dict]):
        return merge_imported_cash_movements_append_only(
            db_path=self.db_path,
            imported_movements=imported_movements,
        )
