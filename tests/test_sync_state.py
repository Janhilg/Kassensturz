from pathlib import Path

from core.admin_service import sync_exports_now
from core.storage import ensure_db_file, insert_entry
from core.sync_state import load_sync_state


class DummyConfig:
    NEXTCLOUD_BASE_URL = "https://example.test"
    NEXTCLOUD_USERNAME = "user"
    NEXTCLOUD_APP_PASSWORD = "pass"
    NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz/Kassensturz_data"
    NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
    NEXTCLOUD_VERIFY = "true"
    NEXTCLOUD_CA_CERT_PATH = ""


def make_entry(i: int):
    return {
        "id": f"id-{i}",
        "date": "2026-04-28",
        "timestamp": f"2026-04-28 10:00:0{i}",
        "event_name": "Test",
        "counted_by": "Tester",
        "cash_sum": 10.0,
        "event_status": "opening",
        "comment": "",
        "denom_100": None,
        "denom_50": None,
        "denom_20": None,
        "denom_10": None,
        "denom_5": None,
        "denom_2": None,
        "denom_1": None,
        "denom_050": None,
        "denom_020": None,
        "denom_010": None,
    }


def test_sync_state_counts_new_rows(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "data" / "kassensturz.db"
    excel_path = tmp_path / "data" / "kassensturz_data.xlsx"
    text_path = tmp_path / "data" / "kassensturz_data.txt"
    sync_state_file = tmp_path / "data" / "sync_state.json"

    # prevent real uploads
    monkeypatch.setattr(
        "core.admin_service.upload_excel_file_to_nextcloud",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "core.admin_service.upload_text_file_to_nextcloud",
        lambda *args, **kwargs: None,
    )

    ensure_db_file(db_path)

    for i in range(3):
        insert_entry(db_path, make_entry(i))

    result1 = sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=DummyConfig(),
        base_dir=tmp_path,
        sync_state_file=sync_state_file,
    )

    assert result1["uploaded_total_rows"] == 3
    assert result1["new_rows_added_to_shared_dataset"] == 3

    state = load_sync_state(sync_state_file)
    assert state["last_uploaded_row_count"] == 3

    result2 = sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=DummyConfig(),
        base_dir=tmp_path,
        sync_state_file=sync_state_file,
    )

    assert result2["uploaded_total_rows"] == 3
    assert result2["new_rows_added_to_shared_dataset"] == 0

    insert_entry(db_path, make_entry(99))

    result3 = sync_exports_now(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        config=DummyConfig(),
        base_dir=tmp_path,
        sync_state_file=sync_state_file,
    )

    assert result3["uploaded_total_rows"] == 4
    assert result3["new_rows_added_to_shared_dataset"] == 1