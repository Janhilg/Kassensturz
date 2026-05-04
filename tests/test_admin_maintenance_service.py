from core.admin_maintenance_service import AdminMaintenanceService


class RecordingStorage:
    def __init__(self, calls, row_counts=None):
        self.calls = calls
        self.row_counts = row_counts or {
            "cash_accounts": 2,
            "cash_contexts": 1,
            "cash_movements": 3,
            "cash_counts": 4,
        }

    def ensure_db_file(self, db_path):
        self.calls.append(("ensure_db_file", db_path))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

    def get_row_count(self, db_path, table_name):
        self.calls.append(("get_row_count", table_name))
        return self.row_counts[table_name]

    def list_backups(self, backup_dir):
        self.calls.append(("list_backups", backup_dir))
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / "kassensturz_backup_20260504_080000.db"
        backup.write_bytes(b"backup")
        return [backup]

    def get_schema_version(self, db_path):
        self.calls.append(("get_schema_version", db_path))
        return 1

    def restore_backup(self, **kwargs):
        self.calls.append(("restore_backup", kwargs["backup_file"], kwargs["db_path"]))


class RecordingExportService:
    def __init__(self, calls):
        self.calls = calls

    def export_all(self, **kwargs):
        self.calls.append(("export_all", kwargs["excel_path"], kwargs["text_path"]))
        kwargs["excel_path"].write_bytes(b"excel")
        kwargs["text_path"].write_text("text", encoding="utf-8")


class RecordingNextcloudClient:
    def __init__(self, calls, configured):
        self.calls = calls
        self.configured = configured

    def nextcloud_configured(self, config):
        self.calls.append(("nextcloud_configured",))
        return self.configured

    def upload_excel_file_to_nextcloud(self, config, base_dir, file_path):
        self.calls.append(("upload_excel", base_dir, file_path))
        return {"uploaded": True, "file": file_path.name}

    def upload_text_file_to_nextcloud(self, config, base_dir, file_path):
        self.calls.append(("upload_text", base_dir, file_path))
        return {"uploaded": True, "file": file_path.name}


class RecordingSyncStateStore:
    def __init__(self, calls):
        self.calls = calls

    def update_sync_state(self, sync_state_file, updates):
        self.calls.append(("update_sync_state", sync_state_file, updates))


def test_admin_human_size_formats_boundaries():
    service = AdminMaintenanceService()

    assert service.human_size(0) == "0.0 B"
    assert service.human_size(1023) == "1023.0 B"
    assert service.human_size(1024) == "1.0 KB"
    assert service.human_size(1024 * 1024) == "1.0 MB"
    assert service.human_size(1024 * 1024 * 1024) == "1.0 GB"
    assert service.human_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


def test_admin_sync_exports_now_records_unconfigured_upload_result(
    tmp_path,
    db_path,
    excel_path,
    text_path,
    sync_state_file,
    config_stub,
):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=RecordingStorage(calls),
        export_service=RecordingExportService(calls),
        nextcloud_client=RecordingNextcloudClient(calls, configured=False),
        sync_state_store=RecordingSyncStateStore(calls),
    )

    result = service.sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=config_stub,
        base_dir=tmp_path,
        sync_state_file=sync_state_file,
    )

    assert result == {
        "uploaded_total_rows": 7,
        "uploaded": {"uploaded": False, "reason": "nextcloud_not_configured"},
    }
    assert [call[0] for call in calls] == [
        "ensure_db_file",
        "ensure_db_file",
        "export_all",
        "get_row_count",
        "get_row_count",
        "nextcloud_configured",
        "update_sync_state",
    ]
    assert calls[-1][2] == {
        "uploaded_total_rows": 7,
        "uploaded": {"uploaded": False, "reason": "nextcloud_not_configured"},
    }


def test_admin_sync_exports_now_uploads_both_exports_when_configured(
    tmp_path,
    db_path,
    excel_path,
    text_path,
    sync_state_file,
    config_stub,
):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=RecordingStorage(calls, row_counts={"cash_counts": 5, "cash_movements": 6}),
        export_service=RecordingExportService(calls),
        nextcloud_client=RecordingNextcloudClient(calls, configured=True),
        sync_state_store=RecordingSyncStateStore(calls),
    )

    result = service.sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=config_stub,
        base_dir=tmp_path,
        sync_state_file=sync_state_file,
    )

    assert result == {
        "uploaded_total_rows": 11,
        "uploaded": {
            "excel": {"uploaded": True, "file": "export.xlsx"},
            "text": {"uploaded": True, "file": "export.txt"},
        },
    }
    assert [call[0] for call in calls] == [
        "ensure_db_file",
        "ensure_db_file",
        "export_all",
        "get_row_count",
        "get_row_count",
        "nextcloud_configured",
        "upload_excel",
        "upload_text",
        "update_sync_state",
    ]
    assert calls[6] == ("upload_excel", tmp_path, excel_path)
    assert calls[7] == ("upload_text", tmp_path, text_path)
    assert calls[-1][2] == {
        "uploaded_total_rows": 11,
        "uploaded": result["uploaded"],
    }


def test_admin_restore_backup_uploads_rebuilt_exports_when_configured(
    tmp_path,
    db_path,
    excel_path,
    text_path,
    config_stub,
):
    calls = []
    service = AdminMaintenanceService(
        storage_repo=RecordingStorage(calls),
        export_service=RecordingExportService(calls),
        nextcloud_client=RecordingNextcloudClient(calls, configured=True),
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
        "upload_excel",
        "upload_text",
    ]
    assert calls[4] == ("upload_excel", tmp_path, excel_path)
    assert calls[5] == ("upload_text", tmp_path, text_path)
