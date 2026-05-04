"""Compatibility guard for the removed legacy entry workflow."""

from core.legacy_entry_sync_service import LegacyEntrySyncService

_legacy_entry_sync_service = LegacyEntrySyncService()


def append_and_sync(**kwargs):
    return _legacy_entry_sync_service.append_and_sync(**kwargs)


__all__ = [
    "LegacyEntrySyncService",
    "append_and_sync",
]
