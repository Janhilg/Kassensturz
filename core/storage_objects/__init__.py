_EXPORTS = {
    "CashAccountRepository": (
        "core.storage_objects.cash_account_repository",
        "CashAccountRepository",
    ),
    "CashBackupRepository": (
        "core.storage_objects.cash_backup_repository",
        "CashBackupRepository",
    ),
    "CashContextRepository": (
        "core.storage_objects.cash_context_repository",
        "CashContextRepository",
    ),
    "CashCountRepository": (
        "core.storage_objects.cash_count_repository",
        "CashCountRepository",
    ),
    "CashMovementRepository": (
        "core.storage_objects.cash_movement_repository",
        "CashMovementRepository",
    ),
    "CashStorage": ("core.storage_objects.cash_storage", "CashStorage"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)

    module_name, object_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[object_name])
    return getattr(module, object_name)


__all__ = [
    "CashAccountRepository",
    "CashBackupRepository",
    "CashContextRepository",
    "CashCountRepository",
    "CashMovementRepository",
    "CashStorage",
]
