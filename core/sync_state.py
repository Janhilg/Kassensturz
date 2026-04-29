import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_sync_state(sync_state_file: Path) -> dict:
    if not sync_state_file.exists():
        return {}

    try:
        return json.loads(sync_state_file.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load sync state | file=%s", sync_state_file)
        return {}


def save_sync_state(sync_state_file: Path, state: dict):
    sync_state_file.parent.mkdir(parents=True, exist_ok=True)
    sync_state_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Sync state saved | file=%s", sync_state_file)


def update_sync_state(sync_state_file: Path, updates: dict):
    state = load_sync_state(sync_state_file)
    state.update(updates)
    save_sync_state(sync_state_file, state)
    logger.info("Sync state updated | updates=%s", updates)