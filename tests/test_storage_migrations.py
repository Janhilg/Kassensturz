import sqlite3

import pytest

from core import storage
from core.version import APP_VERSION, DB_SCHEMA_VERSION


def test_version_module_exports_app_and_schema_versions():
    assert APP_VERSION
    assert DB_SCHEMA_VERSION == storage.SCHEMA_VERSION


def test_ensure_db_file_sets_schema_version_for_new_database(db_path):
    storage.ensure_db_file(db_path)

    assert storage.get_schema_version(db_path) == DB_SCHEMA_VERSION


def test_ensure_db_file_migrates_unversioned_account_table(tmp_path):
    db_path = tmp_path / "legacy.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE cash_accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.execute(
            "INSERT INTO cash_accounts (id, name) VALUES (?, ?)",
            ("legacy-account", "Legacy Cash Box"),
        )
        conn.commit()

    storage.ensure_db_file(db_path)

    assert storage.get_schema_version(db_path) == DB_SCHEMA_VERSION
    account = storage.fetch_cash_account_by_id(db_path, "legacy-account")
    assert account["name"] == "Legacy Cash Box"
    assert account["account_type"] == "cash_box"
    assert account["current_balance_cents"] == 0
    assert account["is_active"] == 1
    assert account["created_at"]


def test_ensure_db_file_rejects_newer_schema_version(tmp_path):
    db_path = tmp_path / "future.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION + 1}")
        conn.commit()

    with pytest.raises(RuntimeError, match="newer than this app supports"):
        storage.ensure_db_file(db_path)
