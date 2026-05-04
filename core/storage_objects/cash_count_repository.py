from core.storage_counts import (
    build_cash_count_record,
    create_cash_count,
    fetch_all_cash_counts,
    fetch_cash_counts_by_context_id,
    fetch_recent_cash_counts,
    insert_cash_count,
    merge_imported_cash_counts_append_only,
)
from core.storage_objects.bound_repository import _BoundRepository


class CashCountRepository(_BoundRepository):
    def build(self, **kwargs) -> dict:
        return build_cash_count_record(**kwargs)

    def insert(self, count_record: dict) -> str:
        return insert_cash_count(self.db_path, count_record)

    def create(self, **kwargs) -> str:
        return create_cash_count(self.db_path, **kwargs)

    def all(self) -> list[dict]:
        return fetch_all_cash_counts(self.db_path)

    def by_context_id(self, context_id: str) -> list[dict]:
        return fetch_cash_counts_by_context_id(self.db_path, context_id)

    def recent(self, *, limit: int = 50) -> list[dict]:
        return fetch_recent_cash_counts(self.db_path, limit=limit)

    def merge_imported_append_only(self, imported_counts: list[dict]):
        return merge_imported_cash_counts_append_only(
            db_path=self.db_path,
            imported_counts=imported_counts,
        )
