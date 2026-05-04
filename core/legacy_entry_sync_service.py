class LegacyEntrySyncService:
    def append_and_sync(self, **kwargs):
        raise RuntimeError(
            "core.service.append_and_sync belongs to the legacy entry workflow. "
            "Use core.cash_service.CashService for cash counts and cash movements."
        )
