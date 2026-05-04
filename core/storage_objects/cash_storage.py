from pathlib import Path

from core.storage_objects.cash_account_repository import CashAccountRepository
from core.storage_objects.cash_backup_repository import CashBackupRepository
from core.storage_objects.cash_context_repository import CashContextRepository
from core.storage_objects.cash_count_repository import CashCountRepository
from core.storage_objects.cash_movement_repository import CashMovementRepository
from core.storage_schema import (
    CASH_ACCOUNT_COLUMNS,
    CASH_CONTEXT_COLUMNS,
    CASH_COUNT_COLUMNS,
    CASH_MOVEMENT_COLUMNS,
    DENOM_FIELDS,
    DENOM_VALUE_CENTS,
)
from core.version import DB_SCHEMA_VERSION

SCHEMA_VERSION = DB_SCHEMA_VERSION


def _storage_function(name: str):
    def wrapper(*args, **kwargs):
        from core import storage

        return getattr(storage, name)(*args, **kwargs)

    return wrapper


now_iso = _storage_function("now_iso")
new_id = _storage_function("new_id")
get_connection = _storage_function("get_connection")
dicts_from_rows = _storage_function("dicts_from_rows")
parse_optional_int = _storage_function("parse_optional_int")
normalize_optional_text = _storage_function("normalize_optional_text")
normalize_context_label = _storage_function("normalize_context_label")
cents_to_eur = _storage_function("cents_to_eur")
eur_to_cents = _storage_function("eur_to_cents")
row_values = _storage_function("row_values")
get_denomination_values_from_form = _storage_function("get_denomination_values_from_form")
calculate_total_cents_from_denominations = _storage_function(
    "calculate_total_cents_from_denominations"
)
denominations_match_total_cents = _storage_function("denominations_match_total_cents")
build_cash_movement_record = _storage_function("build_cash_movement_record")
build_cash_count_record = _storage_function("build_cash_count_record")
get_schema_version = _storage_function("get_schema_version")
migrate_database = _storage_function("migrate_database")
ensure_db_file = _storage_function("ensure_db_file")
insert_cash_account = _storage_function("insert_cash_account")
fetch_all_cash_accounts = _storage_function("fetch_all_cash_accounts")
fetch_cash_accounts_by_type = _storage_function("fetch_cash_accounts_by_type")
fetch_cash_account_by_id = _storage_function("fetch_cash_account_by_id")
fetch_cash_account_by_name = _storage_function("fetch_cash_account_by_name")
require_cash_account_by_name = _storage_function("require_cash_account_by_name")
update_cash_account_active_state = _storage_function("update_cash_account_active_state")
seed_default_cash_accounts = _storage_function("seed_default_cash_accounts")
insert_cash_context = _storage_function("insert_cash_context")
fetch_cash_context_by_id = _storage_function("fetch_cash_context_by_id")
fetch_recent_cash_contexts = _storage_function("fetch_recent_cash_contexts")
find_latest_cash_context_by_label = _storage_function("find_latest_cash_context_by_label")
touch_cash_context = _storage_function("touch_cash_context")
get_or_create_cash_context = _storage_function("get_or_create_cash_context")
get_latest_cash_context_label = _storage_function("get_latest_cash_context_label")
insert_cash_movement = _storage_function("insert_cash_movement")
create_cash_movement = _storage_function("create_cash_movement")
fetch_all_cash_movements = _storage_function("fetch_all_cash_movements")
fetch_cash_movements_by_context_id = _storage_function("fetch_cash_movements_by_context_id")
fetch_recent_cash_movements = _storage_function("fetch_recent_cash_movements")
merge_imported_cash_movements_append_only = _storage_function(
    "merge_imported_cash_movements_append_only"
)
merge_imported_cash_contexts_append_only = _storage_function(
    "merge_imported_cash_contexts_append_only"
)
merge_imported_cash_accounts_append_only = _storage_function(
    "merge_imported_cash_accounts_append_only"
)
merge_imported_cash_counts_append_only = _storage_function("merge_imported_cash_counts_append_only")
insert_cash_count = _storage_function("insert_cash_count")
create_cash_count = _storage_function("create_cash_count")
fetch_all_cash_counts = _storage_function("fetch_all_cash_counts")
fetch_cash_counts_by_context_id = _storage_function("fetch_cash_counts_by_context_id")
fetch_recent_cash_counts = _storage_function("fetch_recent_cash_counts")
set_cash_account_balance_cents = _storage_function("set_cash_account_balance_cents")
adjust_cash_account_balance_cents = _storage_function("adjust_cash_account_balance_cents")
get_cash_account_balance_cents = _storage_function("get_cash_account_balance_cents")
fetch_cash_account_balances = _storage_function("fetch_cash_account_balances")
fetch_latest_cash_count_for_account = _storage_function("fetch_latest_cash_count_for_account")
fetch_cash_account_statement = _storage_function("fetch_cash_account_statement")
get_row_count = _storage_function("get_row_count")
create_backup = _storage_function("create_backup")
list_backups = _storage_function("list_backups")
restore_backup = _storage_function("restore_backup")


class CashStorage:
    SCHEMA_VERSION = SCHEMA_VERSION
    DENOM_FIELDS = DENOM_FIELDS
    DENOM_VALUE_CENTS = DENOM_VALUE_CENTS
    CASH_ACCOUNT_COLUMNS = CASH_ACCOUNT_COLUMNS
    CASH_CONTEXT_COLUMNS = CASH_CONTEXT_COLUMNS
    CASH_MOVEMENT_COLUMNS = CASH_MOVEMENT_COLUMNS
    CASH_COUNT_COLUMNS = CASH_COUNT_COLUMNS

    now_iso = staticmethod(now_iso)
    new_id = staticmethod(new_id)
    get_connection = staticmethod(get_connection)
    dicts_from_rows = staticmethod(dicts_from_rows)
    parse_optional_int = staticmethod(parse_optional_int)
    normalize_optional_text = staticmethod(normalize_optional_text)
    normalize_context_label = staticmethod(normalize_context_label)
    cents_to_eur = staticmethod(cents_to_eur)
    eur_to_cents = staticmethod(eur_to_cents)
    row_values = staticmethod(row_values)
    get_schema_version = staticmethod(get_schema_version)
    migrate_database = staticmethod(migrate_database)

    get_denomination_values_from_form = staticmethod(get_denomination_values_from_form)
    calculate_total_cents_from_denominations = staticmethod(
        calculate_total_cents_from_denominations
    )
    denominations_match_total_cents = staticmethod(denominations_match_total_cents)

    build_cash_movement_record = staticmethod(build_cash_movement_record)
    build_cash_count_record = staticmethod(build_cash_count_record)

    def __init__(self, db_path: Path | None = None):
        self.db_path: Path | None = None
        self.accounts: CashAccountRepository | None = None
        self.contexts: CashContextRepository | None = None
        self.movements: CashMovementRepository | None = None
        self.counts: CashCountRepository | None = None
        self.backups: CashBackupRepository | None = None

        if db_path is not None:
            self.configure(db_path)

    def configure(self, db_path: Path):
        self.db_path = Path(db_path)
        self.accounts = CashAccountRepository(self.db_path)
        self.contexts = CashContextRepository(self.db_path)
        self.movements = CashMovementRepository(self.db_path)
        self.counts = CashCountRepository(self.db_path)
        self.backups = CashBackupRepository(self.db_path)

    def bind(self, db_path: Path) -> "CashStorage":
        return CashStorage(db_path)

    @property
    def is_bound(self) -> bool:
        return self.db_path is not None

    def _path(self, db_path: Path | None = None) -> Path:
        resolved = db_path or self.db_path
        if resolved is None:
            raise ValueError("db_path is required for unbound CashStorage")
        return Path(resolved)

    def ensure_db_file(self, db_path: Path | None = None):
        return ensure_db_file(self._path(db_path))

    def schema_version(self, db_path: Path | None = None) -> int:
        return get_schema_version(self._path(db_path))

    def insert_cash_account(self, db_path: Path | None = None, **kwargs) -> str:
        return insert_cash_account(self._path(db_path), **kwargs)

    def fetch_all_cash_accounts(
        self,
        db_path: Path | None = None,
        active_only: bool = False,
    ) -> list[dict]:
        return fetch_all_cash_accounts(self._path(db_path), active_only=active_only)

    def fetch_cash_accounts_by_type(
        self,
        db_path: Path | str | None = None,
        account_type: str | None = None,
        active_only: bool = True,
    ) -> list[dict]:
        if account_type is None:
            account_type = str(db_path)
            db_path = None

        return fetch_cash_accounts_by_type(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_type,
            active_only=active_only,
        )

    def fetch_cash_account_by_id(
        self,
        db_path: Path | str | None = None,
        account_id: str | None = None,
    ) -> dict | None:
        if account_id is None:
            account_id = str(db_path)
            db_path = None

        return fetch_cash_account_by_id(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_id,
        )

    def fetch_cash_account_by_name(
        self,
        db_path: Path | str | None = None,
        name: str | None = None,
    ) -> dict | None:
        if name is None:
            name = str(db_path)
            db_path = None

        return fetch_cash_account_by_name(
            self._path(db_path if isinstance(db_path, Path) else None),
            name,
        )

    def require_cash_account_by_name(
        self,
        db_path: Path | str | None = None,
        name: str | None = None,
    ) -> dict:
        if name is None:
            name = str(db_path)
            db_path = None

        return require_cash_account_by_name(
            self._path(db_path if isinstance(db_path, Path) else None),
            name,
        )

    def update_cash_account_active_state(
        self,
        db_path: Path | None = None,
        **kwargs,
    ):
        return update_cash_account_active_state(self._path(db_path), **kwargs)

    def seed_default_cash_accounts(self, db_path: Path | None = None):
        return seed_default_cash_accounts(self._path(db_path))

    def insert_cash_context(self, db_path: Path | None = None, **kwargs) -> str:
        return insert_cash_context(self._path(db_path), **kwargs)

    def fetch_cash_context_by_id(
        self,
        db_path: Path | str | None = None,
        context_id: str | None = None,
    ) -> dict | None:
        if context_id is None:
            context_id = str(db_path)
            db_path = None

        return fetch_cash_context_by_id(
            self._path(db_path if isinstance(db_path, Path) else None),
            context_id,
        )

    def fetch_recent_cash_contexts(
        self,
        db_path: Path | None = None,
        limit: int = 20,
    ) -> list[dict]:
        return fetch_recent_cash_contexts(self._path(db_path), limit=limit)

    def find_latest_cash_context_by_label(
        self,
        db_path: Path | str | None = None,
        label: str | None = None,
    ) -> dict | None:
        if label is None:
            label = str(db_path)
            db_path = None

        return find_latest_cash_context_by_label(
            self._path(db_path if isinstance(db_path, Path) else None),
            label,
        )

    def touch_cash_context(self, db_path: Path | None = None, **kwargs):
        return touch_cash_context(self._path(db_path), **kwargs)

    def get_or_create_cash_context(
        self,
        db_path: Path | str | None = None,
        label: str | None = None,
    ) -> tuple[str | None, str]:
        if label is None:
            label = str(db_path)
            db_path = None

        return get_or_create_cash_context(
            self._path(db_path if isinstance(db_path, Path) else None),
            label,
        )

    def get_latest_cash_context_label(self, db_path: Path | None = None) -> str:
        return get_latest_cash_context_label(self._path(db_path))

    def insert_cash_movement(self, db_path: Path | None = None, **kwargs) -> str:
        return insert_cash_movement(self._path(db_path), **kwargs)

    def create_cash_movement(self, db_path: Path | None = None, **kwargs) -> str:
        return create_cash_movement(self._path(db_path), **kwargs)

    def fetch_all_cash_movements(self, db_path: Path | None = None) -> list[dict]:
        return fetch_all_cash_movements(self._path(db_path))

    def fetch_cash_movements_by_context_id(
        self,
        db_path: Path | str | None = None,
        context_id: str | None = None,
    ) -> list[dict]:
        if context_id is None:
            context_id = str(db_path)
            db_path = None

        return fetch_cash_movements_by_context_id(
            self._path(db_path if isinstance(db_path, Path) else None),
            context_id,
        )

    def fetch_recent_cash_movements(
        self,
        db_path: Path | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return fetch_recent_cash_movements(self._path(db_path), limit=limit)

    def merge_imported_cash_movements_append_only(
        self,
        db_path: Path | None = None,
        **kwargs,
    ):
        return merge_imported_cash_movements_append_only(self._path(db_path), **kwargs)

    def merge_imported_cash_contexts_append_only(
        self,
        db_path: Path | None = None,
        **kwargs,
    ):
        return merge_imported_cash_contexts_append_only(self._path(db_path), **kwargs)

    def merge_imported_cash_accounts_append_only(
        self,
        db_path: Path | None = None,
        **kwargs,
    ):
        return merge_imported_cash_accounts_append_only(self._path(db_path), **kwargs)

    def merge_imported_cash_counts_append_only(
        self,
        db_path: Path | None = None,
        **kwargs,
    ):
        return merge_imported_cash_counts_append_only(self._path(db_path), **kwargs)

    def insert_cash_count(self, db_path: Path | None = None, **kwargs) -> str:
        return insert_cash_count(self._path(db_path), **kwargs)

    def create_cash_count(self, db_path: Path | None = None, **kwargs) -> str:
        return create_cash_count(self._path(db_path), **kwargs)

    def fetch_all_cash_counts(self, db_path: Path | None = None) -> list[dict]:
        return fetch_all_cash_counts(self._path(db_path))

    def fetch_cash_counts_by_context_id(
        self,
        db_path: Path | str | None = None,
        context_id: str | None = None,
    ) -> list[dict]:
        if context_id is None:
            context_id = str(db_path)
            db_path = None

        return fetch_cash_counts_by_context_id(
            self._path(db_path if isinstance(db_path, Path) else None),
            context_id,
        )

    def fetch_recent_cash_counts(
        self,
        db_path: Path | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return fetch_recent_cash_counts(self._path(db_path), limit=limit)

    def set_cash_account_balance_cents(
        self,
        db_path: Path | str | None = None,
        account_id: str | None = None,
        balance_cents: int | None = None,
    ):
        if balance_cents is None:
            balance_cents = int(account_id)
            account_id = str(db_path)
            db_path = None

        return set_cash_account_balance_cents(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_id,
            int(balance_cents),
        )

    def adjust_cash_account_balance_cents(
        self,
        db_path: Path | str | None = None,
        account_id: str | None = None,
        delta_cents: int | None = None,
    ):
        if delta_cents is None:
            delta_cents = int(account_id)
            account_id = str(db_path)
            db_path = None

        return adjust_cash_account_balance_cents(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_id,
            int(delta_cents),
        )

    def get_cash_account_balance_cents(
        self,
        db_path: Path | str | None = None,
        account_id: str | None = None,
    ) -> int:
        if account_id is None:
            account_id = str(db_path)
            db_path = None

        return get_cash_account_balance_cents(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_id,
        )

    def fetch_cash_account_balances(self, db_path: Path | None = None) -> list[dict]:
        return fetch_cash_account_balances(self._path(db_path))

    def fetch_latest_cash_count_for_account(
        self,
        db_path: Path | str | None = None,
        cash_account_id: str | None = None,
    ) -> dict | None:
        if cash_account_id is None:
            cash_account_id = str(db_path)
            db_path = None

        return fetch_latest_cash_count_for_account(
            self._path(db_path if isinstance(db_path, Path) else None),
            cash_account_id,
        )

    def fetch_cash_account_statement(
        self,
        db_path: Path | str | None = None,
        account_id: str | None = None,
    ) -> dict:
        if account_id is None:
            account_id = str(db_path)
            db_path = None

        return fetch_cash_account_statement(
            self._path(db_path if isinstance(db_path, Path) else None),
            account_id,
        )

    def get_row_count(
        self,
        db_path: Path | str | None = None,
        table_name: str | None = None,
    ) -> int:
        if table_name is None:
            table_name = str(db_path)
            db_path = None

        return get_row_count(
            self._path(db_path if isinstance(db_path, Path) else None),
            table_name,
        )

    def create_backup(
        self,
        db_path: Path | None = None,
        backup_dir: Path | None = None,
        max_backups: int = 25,
    ):
        if backup_dir is None:
            backup_dir = Path(db_path)
            db_path = None

        return create_backup(
            self._path(db_path),
            Path(backup_dir),
            max_backups=max_backups,
        )

    def list_backups(self, backup_dir: Path) -> list[Path]:
        return list_backups(backup_dir)

    def restore_backup(
        self,
        db_path: Path | None = None,
        backup_file: Path | None = None,
    ):
        if backup_file is None:
            backup_file = Path(db_path)
            db_path = None

        return restore_backup(self._path(db_path), Path(backup_file))
