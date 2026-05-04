from pathlib import Path

import pytest
import app as app_module

from core import storage



@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@pytest.fixture
def excel_path(tmp_path: Path) -> Path:
    return tmp_path / "export.xlsx"


@pytest.fixture
def text_path(tmp_path: Path) -> Path:
    return tmp_path / "export.txt"


@pytest.fixture
def sync_state_file(tmp_path: Path) -> Path:
    return tmp_path / "sync_state.json"


@pytest.fixture
def seeded_db(db_path: Path) -> Path:
    storage.ensure_db_file(db_path)
    storage.seed_default_cash_accounts(db_path)
    return db_path


@pytest.fixture
def bar_account_id(seeded_db: Path) -> str:
    account = storage.fetch_cash_account_by_name(seeded_db, "Bar Cash Box")
    assert account is not None
    return account["id"]


@pytest.fixture
def entrance_account_id(seeded_db: Path) -> str:
    account = storage.fetch_cash_account_by_name(seeded_db, "Entrance Cash Box")
    assert account is not None
    return account["id"]


@pytest.fixture
def runner_account_id(seeded_db: Path) -> str:
    account = storage.fetch_cash_account_by_name(seeded_db, "Runner Float")
    assert account is not None
    return account["id"]


@pytest.fixture
def supplier_account_id(seeded_db: Path) -> str:
    account = storage.fetch_cash_account_by_name(seeded_db, "Supplier / Drinks Purchase")
    assert account is not None
    return account["id"]


@pytest.fixture
def config_stub():
    class ConfigStub:
        NEXTCLOUD_BASE_URL = ""
        NEXTCLOUD_USERNAME = ""
        NEXTCLOUD_APP_PASSWORD = ""
        NEXTCLOUD_CA_CERT_PATH = ""
        NEXTCLOUD_VERIFY = "false"
        NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz/Debug"
        NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
        MODE = "debug"
        ADMIN_PASSWORD = "admin"

    return ConfigStub

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
        "record_cash_count",
        lambda request: {
            "imported_counts": 0,
            "imported_movements": 0,
            "count_id": "count-1",
        },
    )
    monkeypatch.setattr(
        app_module.web_app,
        "record_cash_movement",
        lambda request: {
            "imported_counts": 0,
            "imported_movements": 0,
            "movement_id": "mov-1",
        },
    )
    monkeypatch.setattr(
        app_module.web_app,
        "rebuild_exports",
        lambda: {"imported_counts": 0, "imported_movements": 0},
    )

    monkeypatch.setitem(app_module.app.config, "TESTING", True)
    app_module.app.secret_key = "test-secret"

    try:
        with app_module.app.test_client() as client:
            yield client
    finally:
        app_module.web_app.configure_paths(original_paths, initialize=False)
