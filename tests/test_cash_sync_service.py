from datetime import date, time

import pytest
from openpyxl import Workbook

from core.cash.cash_sync_context import CashSyncContext
from core.cash.cash_sync_service import CashSyncService
from core.cash_export_service import CashExportService
from core.storage_accounts import fetch_cash_account_by_name
from core.storage_counts import fetch_all_cash_counts
from core.storage_objects.cash_storage import CashStorage
from core.sync_state import load_sync_state
from core.sync_state_store import SyncStateStore


class RecordingStorage:
    def __init__(self, calls):
        self.calls = calls

    def create_backup(self, db_path, backup_dir):
        self.calls.append(("create_backup", db_path, backup_dir))
        return backup_dir / "backup.db"

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


class RecordingExportService:
    def __init__(self, calls, imported_data):
        self.calls = calls
        self.imported_data = imported_data

    def export_all(self, **kwargs):
        self.calls.append(("export_all", kwargs["excel_path"], kwargs["text_path"]))

    def import_all_from_excel(self, excel_path):
        self.calls.append(("import_all_from_excel", excel_path))
        return self.imported_data


class RecordingNextcloudClient:
    def __init__(self, calls, remote_exists):
        self.calls = calls
        self.remote_exists = remote_exists

    def download_remote_excel_if_exists(self, **kwargs):
        self.calls.append(("download_remote", kwargs["local_excel_path"]))
        return self.remote_exists

    def upload_files(self, **kwargs):
        self.calls.append(("upload_files", kwargs["excel_path"], kwargs["text_path"]))
        return {"uploaded": True}


class RecordingSyncStateStore:
    def __init__(self, calls):
        self.calls = calls

    def update_sync_state(self, sync_state_file, updates):
        self.calls.append(("update_sync_state", sync_state_file, updates))


class CopyingNextcloudClient:
    def __init__(self, source_path):
        self.source_path = source_path

    def download_remote_excel_if_exists(self, *, local_excel_path, config):
        local_excel_path.parent.mkdir(parents=True, exist_ok=True)
        local_excel_path.write_bytes(self.source_path.read_bytes())
        return True


class MissingNextcloudClient:
    def download_remote_excel_if_exists(self, *, local_excel_path, config):
        return False


class FailingNextcloudClient:
    def download_remote_excel_if_exists(self, **kwargs):
        raise AssertionError("Nextcloud should not be called")

    def upload_files(self, **kwargs):
        raise AssertionError("Nextcloud should not be called")


class ExistingActivityStorage:
    def __init__(self, calls):
        self.calls = calls

    def get_row_count(self, db_path, table_name):
        self.calls.append(("get_row_count", table_name))
        return {
            "cash_counts": 1,
            "cash_movements": 0,
        }[table_name]


class ProductionConfig:
    MODE = "production"


def _write_legacy_workbook(excel_path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Legacy"
    worksheet.append(
        [
            "Date",
            "Timestamp",
            "Event name",
            "Counted by",
            "Cash sum",
            "Event status",
            "Comment",
        ]
    )
    worksheet.append(
        [
            date(2026, 4, 30),
            time(23, 0),
            "Friday Bar",
            "Jan",
            "250,00",
            "closing",
            "production bootstrap",
        ]
    )
    workbook.save(excel_path)


def test_cash_sync_service_remote_sync_imports_before_second_export(
    db_path,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    calls = []
    sync_context = CashSyncContext(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
    )
    service = CashSyncService(
        storage_repo=RecordingStorage(calls),
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


def test_production_bootstrap_imports_legacy_remote_counts(
    tmp_path,
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
):
    remote_excel_path = tmp_path / "remote-legacy.xlsx"
    _write_legacy_workbook(remote_excel_path)

    sync_context = CashSyncContext(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=ProductionConfig,
    )
    service = CashSyncService(
        storage_repo=CashStorage(seeded_db),
        export_service=CashExportService(),
        nextcloud_client=CopyingNextcloudClient(remote_excel_path),
        sync_state_store=SyncStateStore(),
        sync_context=sync_context,
    )

    result = service.bootstrap_remote_import_if_empty()

    assert result.skipped is False
    assert result.source_format == "legacy_cash_counts"
    assert result.imported_counts == 1
    assert result.imported_movements == 0

    counts = fetch_all_cash_counts(seeded_db)
    assert len(counts) == 1
    assert counts[0]["context_label"] == "Friday Bar"
    assert counts[0]["total_cents"] == 25000

    bar_account = fetch_cash_account_by_name(seeded_db, "Bar Cash Box")
    assert bar_account["current_balance_cents"] == 25000
    assert excel_path.exists()
    assert text_path.exists()

    state = load_sync_state(sync_state_file)
    assert state["bootstrap_imported_counts"] == 1
    assert state["bootstrap_source_format"] == "legacy_cash_counts"
    assert state["bootstrap_last_check"]["status"] == "imported"
    assert state["bootstrap_last_import"]["source_format"] == "legacy_cash_counts"


def test_production_bootstrap_records_missing_remote_status(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
):
    sync_context = CashSyncContext(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=ProductionConfig,
    )
    service = CashSyncService(
        storage_repo=CashStorage(seeded_db),
        export_service=CashExportService(),
        nextcloud_client=MissingNextcloudClient(),
        sync_state_store=SyncStateStore(),
        sync_context=sync_context,
    )

    result = service.bootstrap_remote_import_if_empty()

    assert result.skipped is True
    assert result.reason == "remote_missing"

    state = load_sync_state(sync_state_file)
    assert state["bootstrap_last_check"]["status"] == "skipped"
    assert state["bootstrap_last_check"]["reason"] == "remote_missing"
    assert "bootstrap_last_import" not in state


def test_bootstrap_skips_without_state_update_outside_production(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    calls = []
    sync_context = CashSyncContext(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
    )
    service = CashSyncService(
        storage_repo=ExistingActivityStorage(calls),
        nextcloud_client=FailingNextcloudClient(),
        sync_state_store=RecordingSyncStateStore(calls),
        sync_context=sync_context,
    )

    result = service.bootstrap_remote_import_if_empty()

    assert result.skipped is True
    assert result.reason == "not_production"
    assert calls == []
    assert load_sync_state(sync_state_file) == {}


def test_bootstrap_records_database_not_empty_skip_before_remote_download(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
):
    calls = []
    sync_context = CashSyncContext(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=ProductionConfig,
    )
    service = CashSyncService(
        storage_repo=ExistingActivityStorage(calls),
        nextcloud_client=FailingNextcloudClient(),
        sync_state_store=RecordingSyncStateStore(calls),
        sync_context=sync_context,
    )

    result = service.bootstrap_remote_import_if_empty()

    assert result.skipped is True
    assert result.reason == "database_not_empty"
    assert [call[0] for call in calls] == [
        "get_row_count",
        "get_row_count",
        "update_sync_state",
    ]
    assert calls[0] == ("get_row_count", "cash_counts")
    assert calls[1] == ("get_row_count", "cash_movements")
    assert calls[2][2]["bootstrap_last_check"]["status"] == "skipped"
    assert calls[2][2]["bootstrap_last_check"]["reason"] == "database_not_empty"


def test_cash_sync_service_requires_context_for_rebuild_and_bootstrap():
    service = CashSyncService()

    with pytest.raises(ValueError, match="CashSyncContext is required"):
        service.rebuild_exports()

    with pytest.raises(ValueError, match="CashSyncContext is required"):
        service.bootstrap_remote_import_if_empty()


def test_cash_sync_service_can_configure_context_after_construction(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
):
    sync_context = CashSyncContext(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
    )
    service = CashSyncService()

    service.configure_sync_context(sync_context)

    assert service.sync_context is sync_context
