from datetime import date, time

from openpyxl import Workbook

from core import sync_state
from core.cash.cash_sync_context import CashSyncContext
from core.cash.cash_sync_service import CashSyncService
from core.cash_export_service import CashExportService
from core.storage_accounts import fetch_cash_account_by_name
from core.storage_counts import fetch_all_cash_counts
from core.storage_objects.cash_storage import CashStorage
from core.sync_state_store import SyncStateStore


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

    state = sync_state.load_sync_state(sync_state_file)
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

    state = sync_state.load_sync_state(sync_state_file)
    assert state["bootstrap_last_check"]["status"] == "skipped"
    assert state["bootstrap_last_check"]["reason"] == "remote_missing"
    assert "bootstrap_last_import" not in state
