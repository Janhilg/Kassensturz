_EXPORTS = {
    "CashCountRequest": ("core.cash.cash_count_request", "CashCountRequest"),
    "CashCountResult": ("core.cash.cash_count_result", "CashCountResult"),
    "CashMovementRequest": ("core.cash.cash_movement_request", "CashMovementRequest"),
    "CashMovementResult": ("core.cash.cash_movement_result", "CashMovementResult"),
    "CashService": ("core.cash.cash_service", "CashService"),
    "CashSyncContext": ("core.cash.cash_sync_context", "CashSyncContext"),
    "CashSyncService": ("core.cash.cash_sync_service", "CashSyncService"),
    "RemoteBootstrapResult": (
        "core.cash.remote_bootstrap_result",
        "RemoteBootstrapResult",
    ),
    "SyncResult": ("core.cash.sync_result", "SyncResult"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)

    module_name, object_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[object_name])
    return getattr(module, object_name)


__all__ = [
    "CashCountRequest",
    "CashCountResult",
    "CashMovementRequest",
    "CashMovementResult",
    "CashService",
    "CashSyncContext",
    "CashSyncService",
    "RemoteBootstrapResult",
    "SyncResult",
]
