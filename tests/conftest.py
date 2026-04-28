import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

class DummyForm(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class DummyConfig:
    NEXTCLOUD_BASE_URL = ""
    NEXTCLOUD_USERNAME = ""
    NEXTCLOUD_APP_PASSWORD = ""
    NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz/Kassensturz_data"
    NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
    NEXTCLOUD_VERIFY = "true"
    NEXTCLOUD_CA_CERT_PATH = ""


@pytest.fixture
def temp_paths(tmp_path: Path):
    return {
        "base_dir": tmp_path,
        "db_path": tmp_path / "data" / "kassensturz.db",
        "backup_dir": tmp_path / "data" / "backups",
        "excel_path": tmp_path / "data" / "kassensturz_data.xlsx",
        "text_path": tmp_path / "data" / "kassensturz_data.txt",
    }


@pytest.fixture
def sample_entry():
    return {
        "id": "test-id-001",
        "date": "2026-04-28",
        "timestamp": "2026-04-28 10:00:00",
        "event_name": "Barabend",
        "counted_by": "Jan",
        "cash_sum": 83.4,
        "event_status": "opening",
        "comment": "test",
        "denom_100": None,
        "denom_50": 1,
        "denom_20": 1,
        "denom_10": 1,
        "denom_5": 0,
        "denom_2": 1,
        "denom_1": 1,
        "denom_050": 0,
        "denom_020": 2,
        "denom_010": 0,
    }