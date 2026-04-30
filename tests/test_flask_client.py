
import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    excel_path = tmp_path / "export.xlsx"
    text_path = tmp_path / "export.txt"
    backup_dir = tmp_path / "backups"
    sync_state_file = tmp_path / "sync_state.json"

    monkeypatch.setattr(app_module, "LOCAL_DB_FILE", db_path)
    monkeypatch.setattr(app_module, "LOCAL_EXCEL_EXPORT_FILE", excel_path)
    monkeypatch.setattr(app_module, "LOCAL_TEXT_EXPORT_FILE", text_path)
    monkeypatch.setattr(app_module, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(app_module, "SYNC_STATE_FILE", sync_state_file)

    app_module.storage.ensure_db_file(db_path)
    app_module.storage.seed_default_cash_accounts(db_path)

    monkeypatch.setattr(
        app_module,
        "record_cash_count_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0, "count_id": "count-1"},
    )
    monkeypatch.setattr(
        app_module,
        "record_cash_movement_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0, "movement_id": "mov-1"},
    )
    monkeypatch.setattr(
        app_module,
        "rebuild_exports_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0},
    )

    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"

    with app_module.app.test_client() as client:
        yield client