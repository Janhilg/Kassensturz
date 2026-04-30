from core import sync_state


def test_update_sync_state_merges_values(sync_state_file):
    sync_state.update_sync_state(sync_state_file, {"imported_counts": 1})
    sync_state.update_sync_state(sync_state_file, {"imported_movements": 2})

    state = sync_state.load_sync_state(sync_state_file)

    assert state["imported_counts"] == 1
    assert state["imported_movements"] == 2