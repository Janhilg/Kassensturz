from pathlib import Path

from core.cash.cash_sync_context import CashSyncContext


class CashServiceStorage:
    def __init__(self, storage_repo, sync_context: CashSyncContext):
        self.storage_repo = storage_repo
        self.sync_context = sync_context

    def _has_bound_db(self) -> bool:
        return bool(getattr(self.storage_repo, "db_path", None))

    def _call(self, method, *args, **kwargs):
        if self._has_bound_db():
            return method(*args, **kwargs)

        return method(*args, db_path=self.sync_context.db_path, **kwargs)

    def calculate_total_cents_from_denominations(self, denominations: dict) -> int:
        return self.storage_repo.calculate_total_cents_from_denominations(denominations)

    def create_backup(self, backup_dir: Path):
        return self._call(self.storage_repo.create_backup, backup_dir=backup_dir)

    def get_row_count(self, table_name: str) -> int:
        return self._call(self.storage_repo.get_row_count, table_name=table_name)

    def merge_imported_cash_accounts_append_only(self, imported_accounts: list[dict]):
        return self._call(
            self.storage_repo.merge_imported_cash_accounts_append_only,
            imported_accounts=imported_accounts,
        )

    def merge_imported_cash_contexts_append_only(self, imported_contexts: list[dict]):
        return self._call(
            self.storage_repo.merge_imported_cash_contexts_append_only,
            imported_contexts=imported_contexts,
        )

    def merge_imported_cash_counts_append_only(self, imported_counts: list[dict]):
        return self._call(
            self.storage_repo.merge_imported_cash_counts_append_only,
            imported_counts=imported_counts,
        )

    def merge_imported_cash_movements_append_only(self, imported_movements: list[dict]):
        return self._call(
            self.storage_repo.merge_imported_cash_movements_append_only,
            imported_movements=imported_movements,
        )

    def fetch_all_cash_counts(self) -> list[dict]:
        return self._call(self.storage_repo.fetch_all_cash_counts)

    def create_cash_count(
        self,
        *,
        cash_account_id: str,
        counted_by: str,
        total_cents: int,
        count_type: str,
        context_label: str,
        note: str = "",
        denominations: dict | None = None,
    ) -> str:
        return self._call(
            self.storage_repo.create_cash_count,
            cash_account_id=cash_account_id,
            counted_by=counted_by,
            total_cents=total_cents,
            count_type=count_type,
            context_label=context_label,
            note=note,
            denominations=denominations,
        )

    def set_cash_account_balance_cents(self, *, account_id: str, balance_cents: int):
        return self._call(
            self.storage_repo.set_cash_account_balance_cents,
            account_id=account_id,
            balance_cents=balance_cents,
        )

    def create_cash_movement(
        self,
        *,
        amount_cents: int,
        from_account_id: str | None,
        to_account_id: str | None,
        context_label: str,
        actor: str = "",
        reference: str = "",
        note: str = "",
        denominations: dict | None = None,
    ) -> str:
        return self._call(
            self.storage_repo.create_cash_movement,
            amount_cents=amount_cents,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            context_label=context_label,
            actor=actor,
            reference=reference,
            note=note,
            denominations=denominations,
        )

    def adjust_cash_account_balance_cents(self, *, account_id: str, delta_cents: int):
        return self._call(
            self.storage_repo.adjust_cash_account_balance_cents,
            account_id=account_id,
            delta_cents=delta_cents,
        )

    def fetch_cash_account_by_name(self, name: str) -> dict | None:
        return self._call(self.storage_repo.fetch_cash_account_by_name, name=name)

    def require_cash_account_by_name(self, name: str) -> dict:
        return self._call(self.storage_repo.require_cash_account_by_name, name=name)
