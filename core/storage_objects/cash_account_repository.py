from core.storage_accounts import (
    adjust_cash_account_balance_cents,
    fetch_all_cash_accounts,
    fetch_cash_account_balances,
    fetch_cash_account_by_id,
    fetch_cash_account_by_name,
    fetch_cash_account_statement,
    fetch_cash_accounts_by_type,
    get_cash_account_balance_cents,
    insert_cash_account,
    merge_imported_cash_accounts_append_only,
    require_cash_account_by_name,
    seed_default_cash_accounts,
    set_cash_account_balance_cents,
    update_cash_account_active_state,
)
from core.storage_counts import fetch_latest_cash_count_for_account
from core.storage_objects.bound_repository import _BoundRepository


class CashAccountRepository(_BoundRepository):
    def insert(
        self,
        *,
        name: str,
        account_type: str,
        current_balance_cents: int = 0,
        is_active: int = 1,
        sort_order: int = 0,
        account_id: str | None = None,
    ) -> str:
        return insert_cash_account(
            db_path=self.db_path,
            name=name,
            account_type=account_type,
            current_balance_cents=current_balance_cents,
            is_active=is_active,
            sort_order=sort_order,
            account_id=account_id,
        )

    def all(self, *, active_only: bool = False) -> list[dict]:
        return fetch_all_cash_accounts(self.db_path, active_only=active_only)

    def by_type(self, account_type: str, *, active_only: bool = True) -> list[dict]:
        return fetch_cash_accounts_by_type(
            self.db_path,
            account_type,
            active_only=active_only,
        )

    def by_id(self, account_id: str) -> dict | None:
        return fetch_cash_account_by_id(self.db_path, account_id)

    def by_name(self, name: str) -> dict | None:
        return fetch_cash_account_by_name(self.db_path, name)

    def require_by_name(self, name: str) -> dict:
        return require_cash_account_by_name(self.db_path, name)

    def update_active_state(self, account_id: str, is_active: bool):
        return update_cash_account_active_state(self.db_path, account_id, is_active)

    def seed_defaults(self):
        return seed_default_cash_accounts(self.db_path)

    def set_balance_cents(self, account_id: str, balance_cents: int):
        return set_cash_account_balance_cents(self.db_path, account_id, balance_cents)

    def adjust_balance_cents(self, account_id: str, delta_cents: int):
        return adjust_cash_account_balance_cents(self.db_path, account_id, delta_cents)

    def balance_cents(self, account_id: str) -> int:
        return get_cash_account_balance_cents(self.db_path, account_id)

    def balances(self) -> list[dict]:
        return fetch_cash_account_balances(self.db_path)

    def latest_count(self, account_id: str) -> dict | None:
        return fetch_latest_cash_count_for_account(self.db_path, account_id)

    def statement(self, account_id: str) -> dict:
        return fetch_cash_account_statement(self.db_path, account_id)

    def merge_imported_append_only(self, imported_accounts: list[dict]):
        return merge_imported_cash_accounts_append_only(
            db_path=self.db_path,
            imported_accounts=imported_accounts,
        )
