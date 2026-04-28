import json
from pathlib import Path


def load_sync_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {"last_uploaded_row_count": 0}

    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {"last_uploaded_row_count": 0}


def save_sync_state(state_file: Path, *, last_uploaded_row_count: int):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {"last_uploaded_row_count": last_uploaded_row_count},
            indent=2,
        ),
        encoding="utf-8",
    )