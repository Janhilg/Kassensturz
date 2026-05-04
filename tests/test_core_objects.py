from pathlib import Path

import pytest

from core.admin_service import AdminMaintenanceService
from core.cash.cash_count_request import CashCountRequest
from core.cash.cash_movement_request import CashMovementRequest
from core.cash.cash_service import CashService
from core.cash.cash_sync_context import CashSyncContext
from core.cash_export_service import CashExportService
from core.nextcloud_client import NextcloudClient
from core.storage_objects.cash_storage import CashStorage
from core.sync_state_store import SyncStateStore


class NoopNextcloudClient:
    def download_remote_excel_if_exists(self, *, local_excel_path, config):
        return False

    def upload_files(self, *, excel_path, text_path, config):
        return {
            "excel": {"uploaded": False},
            "text": {"uploaded": False},
        }


class RecordingStorage:
    DENOM_FIELDS = CashStorage.DENOM_FIELDS

    def __init__(self, calls):
        self.calls = calls

    def calculate_total_cents_from_denominations(self, denominations):
        return sum(int(value or 0) for value in denominations.values())

    def create_cash_count(self, **kwargs):
        self.calls.append(("create_cash_count", kwargs["cash_account_id"]))
        return "count-1"

    def set_cash_account_balance_cents(self, **kwargs):
        self.calls.append(("set_balance", kwargs["account_id"], kwargs["balance_cents"]))

    def create_backup(self, db_path, backup_dir):
        self.calls.append(("create_backup", db_path, backup_dir))
        return backup_dir / "backup.db"

    def create_cash_movement(self, **kwargs):
        self.calls.append(
            (
                "create_cash_movement",
                kwargs["from_account_id"],
                kwargs["to_account_id"],
                kwargs["amount_cents"],
            )
        )
        return "movement-1"

    def adjust_cash_account_balance_cents(self, **kwargs):
        self.calls.append(("adjust_balance", kwargs["account_id"], kwargs["delta_cents"]))

    def fetch_cash_account_by_name(self, db_path, name):
        self.calls.append(("fetch_account_by_name", name))
        return None


class RecordingExportService:
    def __init__(self, calls, imported_data=None):
        self.calls = calls
        self.imported_data = imported_data or {
            "cash_accounts": [],
            "cash_contexts": [],
            "cash_counts": [],
            "cash_movements": [],
        }

    def export_all(self, **kwargs):
        self.calls.append(("export_all", kwargs["excel_path"], kwargs["text_path"]))

    def import_all_from_excel(self, excel_path):
        self.calls.append(("import_all_from_excel", excel_path))
        return self.imported_data


class RecordingNextcloudClient:
    def __init__(self, calls, remote_exists=False, configured=False):
        self.calls = calls
        self.remote_exists = remote_exists
        self.configured = configured

    def download_remote_excel_if_exists(self, **kwargs):
        self.calls.append(("download_remote", kwargs["local_excel_path"]))
        return self.remote_exists

    def upload_files(self, **kwargs):
        self.calls.append(("upload_files", kwargs["excel_path"], kwargs["text_path"]))
        return {"uploaded": True}

    def nextcloud_configured(self, config):
        self.calls.append(("nextcloud_configured",))
        return self.configured

    def upload_excel_file_to_nextcloud(self, config, base_dir, file_path):
        self.calls.append(("upload_excel", file_path))
        return {"uploaded": True, "file": file_path.name}

    def upload_text_file_to_nextcloud(self, config, base_dir, file_path):
        self.calls.append(("upload_text", file_path))
        return {"uploaded": True, "file": file_path.name}


class RecordingSyncStateStore:
    def __init__(self, calls):
        self.calls = calls

    def update_sync_state(self, sync_state_file, updates):
        self.calls.append(("update_sync_state", sync_state_file, updates))


class AdminRecordingStorage:
    def __init__(self, calls):
        self.calls = calls

    def ensure_db_file(self, db_path):
        self.calls.append(("ensure_db_file", db_path))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

    def get_row_count(self, db_path, table_name):
        self.calls.append(("get_row_count", table_name))
        return {
            "cash_accounts": 2,
            "cash_contexts": 1,
            "cash_movements": 3,
            "cash_counts": 4,
        }[table_name]

    def get_schema_version(self, db_path):
        self.calls.append(("get_schema_version", db_path))
        return 1

    def list_backups(self, backup_dir):
        self.calls.append(("list_backups", backup_dir))
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / "kassensturz_backup_20260504_080000.db"
        backup.write_bytes(b"backup")
        return [backup]

    def restore_backup(self, **kwargs):
        self.calls.append(("restore_backup", kwargs["backup_file"], kwargs["db_path"]))


def _cash_sync_context(
    db_path,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config,
):
    return CashSyncContext(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )


def test_cash_storage_object_seeds_default_accounts(db_path):
    storage = CashStorage()

    storage.ensure_db_file(db_path)
    storage.seed_default_cash_accounts(db_path)

    account = storage.fetch_cash_account_by_name(db_path, "Bar Cash Box")
    assert account["id"] == "acc_bar_cash_box"


def test_cash_storage_bound_repositories_hide_db_path(db_path):
    storage = CashStorage(db_path)

    storage.ensure_db_file()
    storage.accounts.seed_defaults()
    account = storage.accounts.by_name("Bar Cash Box")
    storage.accounts.set_balance_cents(account["id"], 12345)

    assert storage.fetch_cash_account_by_id(account["id"])["current_balance_cents"] == 12345
    assert storage.accounts.balances()[0]["balance_eur"] >= 0


def test_cash_service_object_records_count(
    db_path,
    backup_dir,
    excel_path,
    text_path,
    sync_state_file,
    config_stub,
):
    storage = CashStorage()
    storage.ensure_db_file(db_path)
    storage.seed_default_cash_accounts(db_path)
    account = storage.fetch_cash_account_by_name(db_path, "Bar Cash Box")
    sync_context = _cash_sync_context(
        db_path,
        excel_path,
        text_path,
        backup_dir,
        sync_state_file,
        config_stub,
    )

    service = CashService(
        storage_repo=storage,
        export_service=CashExportService(),
        nextcloud_client=NoopNextcloudClient(),
        sync_state_store=SyncStateStore(),
        sync_context=sync_context,
    )

    result = service.record_count(
        CashCountRequest(
            cash_account_id=account["id"],
            counted_by="Jan",
            total_cents=12345,
            count_type="opening",
            context_label="Friday Bar",
            denominations=None,
        )
    )

    assert result.count_id
    assert (
        storage.fetch_cash_account_by_id(db_path, account["id"])["current_balance_cents"] == 12345
    )


def test_cash_service_record_count_uses_bound_sync_context(
    db_path,
    backup_dir,
    excel_path,
    text_path,
    sync_state_file,
    config_stub,
):
    storage = CashStorage(db_path)
    storage.ensure_db_file()
    storage.seed_default_cash_accounts()
    account = storage.fetch_cash_account_by_name("Bar Cash Box")
    sync_context = CashSyncContext(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
    )
    service = CashService(
        storage_repo=storage,
        export_service=CashExportService(),
        nextcloud_client=NoopNextcloudClient(),
        sync_state_store=SyncStateStore(),
        sync_context=sync_context,
    )

    result = service.record_count(
        CashCountRequest(
            cash_account_id=account["id"],
            counted_by="Jan",
            total_cents=4321,
            count_type="opening",
            context_label="Saturday Bar",
        )
    )

    assert result.count_id
    assert result.to_dict()["imported_counts"] == 0
    assert storage.fetch_cash_account_by_id(account["id"])["current_balance_cents"] == 4321


def test_cash_service_count_uses_dependencies_in_order(
    db_path,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    calls = []
    sync_context = _cash_sync_context(
        db_path,
        excel_path,
        text_path,
        backup_dir,
        sync_state_file,
        config_stub,
    )
    service = CashService(
        storage_repo=RecordingStorage(calls),
        export_service=RecordingExportService(calls),
        nextcloud_client=RecordingNextcloudClient(calls),
        sync_state_store=RecordingSyncStateStore(calls),
        sync_context=sync_context,
    )

    result = service.record_count(
        CashCountRequest(
            cash_account_id="acc_bar_cash_box",
            counted_by="Jan",
            total_cents=12345,
            count_type="opening",
            context_label="Friday Bar",
            denominations=None,
        )
    )

    assert result.count_id == "count-1"
    assert [call[0] for call in calls] == [
        "create_cash_count",
        "set_balance",
        "create_backup",
        "export_all",
        "download_remote",
        "export_all",
        "upload_files",
        "update_sync_state",
    ]


def test_cash_service_remote_sync_imports_before_second_export(
    db_path,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    class RemoteStorage(RecordingStorage):
        def merge_imported_cash_accounts_append_only(self, **kwargs):
            self.calls.append(("merge_accounts", kwargs["imported_accounts"]))
            return {"imported": 1, "skipped": 0}

        def merge_imported_cash_contexts_append_only(self, **kwargs):
            self.calls.append(("merge_contexts", kwargs["imported_contexts"]))
            return {"imported": 1, "skipped": 0}

        def merge_imported_cash_counts_append_only(self, **kwargs):
            self.calls.append(("merge_counts", kwargs["imported_counts"]))
            return {"imported": 1, "skipped": 0}

        def merge_imported_cash_movements_append_only(self, **kwargs):
            self.calls.append(("merge_movements", kwargs["imported_movements"]))
            return {"imported": 1, "skipped": 0}

    calls = []
    sync_context = _cash_sync_context(
        db_path,
        excel_path,
        text_path,
        backup_dir,
        sync_state_file,
        config_stub,
    )
    service = CashService(
        storage_repo=RemoteStorage(calls),
        export_service=RecordingExportService(
            calls,
            imported_data={
                "cash_accounts": [{"id": "remote-account"}],
                "cash_contexts": [{"id": "remote-context"}],
                "cash_counts": [{"id": "remote-count"}],
                "cash_movements": [{"id": "remote-movement"}],
            },
        ),
        nextcloud_client=RecordingNextcloudClient(calls, remote_exists=True),
        sync_state_store=RecordingSyncStateStore(calls),
        sync_context=sync_context,
    )

    result = service.rebuild_exports()

    assert result.imported_counts == 1
    assert result.imported_movements == 1
    assert [call[0] for call in calls] == [
        "create_backup",
        "export_all",
        "download_remote",
        "import_all_from_excel",
        "merge_accounts",
        "merge_contexts",
        "merge_counts",
        "merge_movements",
        "export_all",
        "upload_files",
        "update_sync_state",
    ]


def test_cash_service_validation_edges(
    db_path,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    sync_context = _cash_sync_context(
        db_path,
        excel_path,
        text_path,
        backup_dir,
        sync_state_file,
        config_stub,
    )
    service = CashService(
        storage_repo=RecordingStorage([]),
        sync_context=sync_context,
    )

    with pytest.raises(ValueError, match="Amount must be > 0"):
        service.record_movement(
            CashMovementRequest(
                from_account_id="source",
                to_account_id="target",
                amount_cents=0,
            )
        )

    with pytest.raises(ValueError, match="same"):
        service.record_movement(
            CashMovementRequest(
                from_account_id="same",
                to_account_id="same",
                amount_cents=1,
            )
        )

    with pytest.raises(ValueError, match="negative"):
        service.record_count(
            CashCountRequest(
                cash_account_id="account",
                counted_by="Jan",
                total_cents=-1,
                count_type="opening",
            )
        )


def test_nextcloud_client_exposes_configuration_helpers(config_stub):
    client = NextcloudClient()

    assert client.nextcloud_configured(config_stub) is False


def test_admin_status_snapshot_reports_row_counts(tmp_path, config_stub):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=AdminRecordingStorage(calls),
        nextcloud_client=RecordingNextcloudClient(calls, configured=False),
    )

    snapshot = service.get_status_snapshot(
        db_path=tmp_path / "test.db",
        backup_dir=tmp_path / "backups",
        excel_path=tmp_path / "export.xlsx",
        text_path=tmp_path / "export.txt",
        config=config_stub,
    )

    assert snapshot["row_counts"] == {
        "cash_accounts": 2,
        "cash_contexts": 1,
        "cash_movements": 3,
        "cash_counts": 4,
    }
    assert snapshot["backup_count"] == 1
    assert snapshot["nextcloud_configured"] is False
    assert snapshot["app_version"]
    assert snapshot["db_schema_version"] == 1
    assert snapshot["supported_db_schema_version"] == 1
    assert ("nextcloud_configured",) in calls


def test_admin_rebuild_exports_delegates_to_export_service(
    db_path,
    excel_path,
    text_path,
):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=AdminRecordingStorage(calls),
        export_service=RecordingExportService(calls),
    )

    service.rebuild_exports(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
    )

    assert [call[0] for call in calls] == ["ensure_db_file", "export_all"]


def test_admin_restore_backup_restores_then_rebuilds_without_nextcloud_upload(
    tmp_path,
    db_path,
    excel_path,
    text_path,
    config_stub,
):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=AdminRecordingStorage(calls),
        export_service=RecordingExportService(calls),
        nextcloud_client=RecordingNextcloudClient(calls, configured=False),
    )
    backup_file = tmp_path / "backup.db"
    backup_file.write_bytes(b"backup")

    service.restore_backup(
        backup_file=backup_file,
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=config_stub,
        base_dir=tmp_path,
    )

    assert [call[0] for call in calls] == [
        "restore_backup",
        "ensure_db_file",
        "export_all",
        "nextcloud_configured",
    ]


def test_legacy_core_modules_are_import_safe():
    import core.admin_service
    import core.service
    import core.storage
    import core.storage_accounts
    import core.storage_connection
    import core.storage_contexts
    import core.storage_counts
    import core.storage_migrations
    import core.storage_movements

    assert core.admin_service.AdminMaintenanceService
    assert core.service.LegacyEntrySyncService
    assert core.storage.ensure_db_file is core.storage_migrations.ensure_db_file
    assert (
        core.storage.merge_imported_cash_accounts_append_only
        is core.storage_accounts.merge_imported_cash_accounts_append_only
    )
    assert core.storage.create_cash_count is core.storage_counts.create_cash_count
    assert core.storage.create_cash_movement is core.storage_movements.create_cash_movement


def test_storage_repositories_use_direct_storage_modules():
    repository_dir = Path(__file__).resolve().parents[1] / "core" / "storage_objects"
    repository_files = sorted(repository_dir.glob("*_repository.py"))

    assert repository_files
    for repository_file in repository_files:
        source = repository_file.read_text(encoding="utf-8")
        assert "from core import storage" not in source
        assert "import core.storage" not in source


def test_storage_domain_tests_use_direct_storage_modules():
    tests_dir = Path(__file__).resolve().parent
    storage_test_files = sorted(tests_dir.glob("test_storage_*.py"))

    assert storage_test_files
    for storage_test_file in storage_test_files:
        source = storage_test_file.read_text(encoding="utf-8")
        assert "from core import storage" not in source
        assert "import core.storage" not in source


def test_legacy_append_and_sync_raises_clear_error():
    import core.service

    with pytest.raises(RuntimeError, match="legacy entry workflow"):
        core.service.append_and_sync(entry={})
