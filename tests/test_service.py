from core.service import append_and_sync
from core.storage import fetch_all_entries


class DummyConfig:
    NEXTCLOUD_BASE_URL = ""
    NEXTCLOUD_USERNAME = ""
    NEXTCLOUD_APP_PASSWORD = ""
    NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz/Kassensturz_data"
    NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
    NEXTCLOUD_VERIFY = "true"
    NEXTCLOUD_CA_CERT_PATH = ""


def test_append_and_sync_local_only(temp_paths, sample_entry):
    append_and_sync(
        entry=sample_entry,
        db_path=temp_paths["db_path"],
        backup_dir=temp_paths["backup_dir"],
        excel_path=temp_paths["excel_path"],
        text_path=temp_paths["text_path"],
        config=DummyConfig(),
        base_dir=temp_paths["base_dir"],
        is_debug=True,
    )

    rows = fetch_all_entries(temp_paths["db_path"])

    assert len(rows) == 1
    assert temp_paths["excel_path"].exists()
    assert temp_paths["text_path"].exists()
    assert any(temp_paths["backup_dir"].glob("kassensturz_backup_*.db"))


def test_append_and_sync_with_remote_merge(monkeypatch, temp_paths, sample_entry):
    from openpyxl import Workbook
    from core import service

    remote_excel = temp_paths["base_dir"] / "remote.xlsx"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Kassensturz"
    sheet.append([
        "ID", "Date", "Timestamp", "Event name", "Counted by", "Cash sum",
        "Event status", "Comment", "100 €", "50 €", "20 €", "10 €", "5 €",
        "2 €", "1 €", "0.50 €", "0.20 €", "0.10 €"
    ])
    sheet.append([
        "remote-id-001", "2026-04-28", "2026-04-28 09:00:00", "Remote Event",
        "Alex", 50.0, "closing", "remote", "", 1, "", "", "", "", "", "", "", ""
    ])
    workbook.save(remote_excel)

    monkeypatch.setattr(service, "nextcloud_configured", lambda config: True)

    def fake_download(config, base_dir, temp_path):
        temp_path.write_bytes(remote_excel.read_bytes())
        return True

    monkeypatch.setattr(service, "download_remote_excel_to_temp", fake_download)
    monkeypatch.setattr(service, "upload_excel_file_to_nextcloud", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "upload_text_file_to_nextcloud", lambda *args, **kwargs: None)

    append_and_sync(
        entry=sample_entry,
        db_path=temp_paths["db_path"],
        backup_dir=temp_paths["backup_dir"],
        excel_path=temp_paths["excel_path"],
        text_path=temp_paths["text_path"],
        config=object(),
        base_dir=temp_paths["base_dir"],
        is_debug=False,
    )

    rows = fetch_all_entries(temp_paths["db_path"])
    ids = {row["id"] for row in rows}

    assert ids == {"test-id-001", "remote-id-001"}