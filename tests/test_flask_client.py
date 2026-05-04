
import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    excel_path = tmp_path / "export.xlsx"
    text_path = tmp_path / "export.txt"
    backup_dir = tmp_path / "backups"
    sync_state_file = tmp_path / "sync_state.json"
    original_paths = app_module.web_app.paths

    app_module.web_app.configure_paths(
        app_module.AppPaths.from_files(
            base_dir=tmp_path,
            db_file=db_path,
            excel_export_file=excel_path,
            text_export_file=text_path,
            backup_dir=backup_dir,
            sync_state_file=sync_state_file,
        )
    )

    monkeypatch.setattr(
        app_module.web_app,
        "record_cash_count_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0, "count_id": "count-1"},
    )
    monkeypatch.setattr(
        app_module.web_app,
        "record_cash_movement_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0, "movement_id": "mov-1"},
    )
    monkeypatch.setattr(
        app_module.web_app,
        "rebuild_exports_and_sync",
        lambda **kwargs: {"imported_counts": 0, "imported_movements": 0},
    )

    monkeypatch.setitem(app_module.app.config, "TESTING", True)
    app_module.app.secret_key = "test-secret"

    try:
        with app_module.app.test_client() as client:
            yield client
    finally:
        app_module.web_app.configure_paths(original_paths, initialize=False)
