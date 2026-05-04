import sqlite3

import pytest

from core.storage_accounts import fetch_cash_account_by_id
from core.storage_migrations import SCHEMA_VERSION, ensure_db_file, get_schema_version
from core.version import APP_VERSION, DB_SCHEMA_VERSION


def test_version_module_exports_app_and_schema_versions():
    assert APP_VERSION
    assert DB_SCHEMA_VERSION == SCHEMA_VERSION


def test_ensure_db_file_sets_schema_version_for_new_database(db_path):
    ensure_db_file(db_path)

    assert get_schema_version(db_path) == DB_SCHEMA_VERSION


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

    ensure_db_file(db_path)

    assert get_schema_version(db_path) == DB_SCHEMA_VERSION
    account = fetch_cash_account_by_id(db_path, "legacy-account")
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
        ensure_db_file(db_path)
