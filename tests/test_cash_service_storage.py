from core.cash.cash_service_storage import CashServiceStorage
from core.cash.cash_sync_context import CashSyncContext


class RecordingStorage:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.calls = []

    def create_backup(self, **kwargs):
        self.calls.append(("create_backup", kwargs))
        return kwargs["backup_dir"] / "backup.db"

    def get_row_count(self, **kwargs):
        self.calls.append(("get_row_count", kwargs))
        return 7


def _sync_context(tmp_path):
    return CashSyncContext(
        db_path=tmp_path / "test.db",
        excel_path=tmp_path / "export.xlsx",
        text_path=tmp_path / "export.txt",
        backup_dir=tmp_path / "backups",
        sync_state_file=tmp_path / "sync_state.json",
        config=object(),
    )


def test_cash_service_storage_uses_bound_repo_without_db_path(tmp_path):
    context = _sync_context(tmp_path)
    storage_repo = RecordingStorage(db_path=context.db_path)
    storage = CashServiceStorage(storage_repo, context)

    backup_file = storage.create_backup(context.backup_dir)
    row_count = storage.get_row_count("cash_counts")

    assert backup_file == context.backup_dir / "backup.db"
    assert row_count == 7
    assert storage_repo.calls == [
        ("create_backup", {"backup_dir": context.backup_dir}),
        ("get_row_count", {"table_name": "cash_counts"}),
    ]


def test_cash_service_storage_injects_db_path_for_unbound_repo(tmp_path):
    context = _sync_context(tmp_path)
    storage_repo = RecordingStorage()
    storage = CashServiceStorage(storage_repo, context)

    backup_file = storage.create_backup(context.backup_dir)
    row_count = storage.get_row_count("cash_counts")

    assert backup_file == context.backup_dir / "backup.db"
    assert row_count == 7
    assert storage_repo.calls == [
        (
            "create_backup",
            {
                "db_path": context.db_path,
                "backup_dir": context.backup_dir,
            },
        ),
        (
            "get_row_count",
            {
                "db_path": context.db_path,
                "table_name": "cash_counts",
            },
        ),
    ]
