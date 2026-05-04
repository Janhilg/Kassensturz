from core import sync_state


class SyncStateStore:
    load_sync_state = staticmethod(sync_state.load_sync_state)
    save_sync_state = staticmethod(sync_state.save_sync_state)
    update_sync_state = staticmethod(sync_state.update_sync_state)
