from core.storage_objects.bound_repository import _BoundRepository


class CashContextRepository(_BoundRepository):
    def insert(self, label: str, context_id: str | None = None) -> str:
        from core import storage

        return storage.insert_cash_context(self.db_path, label, context_id=context_id)

    def by_id(self, context_id: str) -> dict | None:
        from core import storage

        return storage.fetch_cash_context_by_id(self.db_path, context_id)

    def recent(self, *, limit: int = 20) -> list[dict]:
        from core import storage

        return storage.fetch_recent_cash_contexts(self.db_path, limit=limit)

    def latest_by_label(self, label: str) -> dict | None:
        from core import storage

        return storage.find_latest_cash_context_by_label(self.db_path, label)

    def touch(self, context_id: str, used_at: str | None = None):
        from core import storage

        return storage.touch_cash_context(self.db_path, context_id, used_at=used_at)

    def get_or_create(self, label: str) -> tuple[str | None, str]:
        from core import storage

        return storage.get_or_create_cash_context(self.db_path, label)

    def latest_label(self) -> str:
        from core import storage

        return storage.get_latest_cash_context_label(self.db_path)

    def merge_imported_append_only(self, imported_contexts: list[dict]):
        from core import storage

        return storage.merge_imported_cash_contexts_append_only(
            db_path=self.db_path,
            imported_contexts=imported_contexts,
        )
