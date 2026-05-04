import logging
import time

from core import export_utils, nextcloud_sync, sync_state
from core.cash.cash_service_storage import CashServiceStorage
from core.cash.cash_sync_context import CashSyncContext
from core.cash.remote_bootstrap_result import RemoteBootstrapResult
from core.cash.sync_result import SyncResult
from core.storage_connection import now_iso
from core.storage_objects.cash_storage import CashStorage

logger = logging.getLogger(__name__)


class CashSyncService:
    def __init__(
        self,
        *,
        storage_repo=None,
        export_service=None,
        nextcloud_client=None,
        sync_state_store=None,
        sync_context: CashSyncContext | None = None,
    ):
        self.storage = storage_repo if storage_repo is not None else CashStorage()
        self.export_service = export_service if export_service is not None else export_utils
        self.nextcloud_client = nextcloud_client if nextcloud_client is not None else nextcloud_sync
        self.sync_state_store = sync_state_store if sync_state_store is not None else sync_state
        self.sync_context = sync_context
        self.logger = logger

    def configure_sync_context(self, sync_context: CashSyncContext):
        self.sync_context = sync_context

    def _context(self, sync_context: CashSyncContext | None = None) -> CashSyncContext:
        resolved = sync_context or self.sync_context
        if resolved is None:
            raise ValueError("CashSyncContext is required")

        return resolved

    def _storage_for(self, sync_context: CashSyncContext) -> CashServiceStorage:
        return CashServiceStorage(self.storage, sync_context)

    def run_full_sync_pipeline(
        self,
        sync_context: CashSyncContext | None = None,
    ) -> SyncResult:
        sync_context = self._context(sync_context)
        storage = self._storage_for(sync_context)
        start_time = time.time()
        self.logger.info("Sync pipeline started | db=%s", sync_context.db_path)

        backup_file = storage.create_backup(sync_context.backup_dir)
        self.logger.info("Backup created | file=%s", backup_file)

        self.export_service.export_all(
            db_path=sync_context.db_path,
            excel_path=sync_context.excel_path,
            text_path=sync_context.text_path,
        )
        self.logger.info(
            "Local export complete | excel=%s text=%s",
            sync_context.excel_path,
            sync_context.text_path,
        )

        remote_exists = self.nextcloud_client.download_remote_excel_if_exists(
            local_excel_path=sync_context.excel_path,
            config=sync_context.config,
        )

        imported_counts = 0
        imported_movements = 0
        remote_count_counts = 0
        remote_count_movements = 0

        if remote_exists:
            self.logger.info("Remote Excel found, starting import")

            remote_data = self.export_service.import_all_from_excel(sync_context.excel_path)
            remote_count_counts = len(remote_data.get("cash_counts", []))
            remote_count_movements = len(remote_data.get("cash_movements", []))

            self.logger.info(
                "Remote data loaded | counts=%s movements=%s",
                remote_count_counts,
                remote_count_movements,
            )
            accounts_result = storage.merge_imported_cash_accounts_append_only(
                imported_accounts=remote_data.get("cash_accounts", []),
            )

            contexts_result = storage.merge_imported_cash_contexts_append_only(
                imported_contexts=remote_data.get("cash_contexts", []),
            )

            counts_result = storage.merge_imported_cash_counts_append_only(
                imported_counts=remote_data.get("cash_counts", []),
            )

            movements_result = storage.merge_imported_cash_movements_append_only(
                imported_movements=remote_data.get("cash_movements", []),
            )

            imported_counts = counts_result["imported"]
            imported_movements = movements_result["imported"]

            self.logger.info(
                "Reference merge summary | accounts imported=%s contexts imported=%s",
                accounts_result["imported"],
                contexts_result["imported"],
            )

            self.logger.info(
                "Merge summary | counts imported=%s skipped=%s | movements imported=%s skipped=%s",
                counts_result["imported"],
                counts_result["skipped"],
                movements_result["imported"],
                movements_result["skipped"],
            )
        else:
            self.logger.info("No remote Excel found")

        self.export_service.export_all(
            db_path=sync_context.db_path,
            excel_path=sync_context.excel_path,
            text_path=sync_context.text_path,
        )
        self.logger.info("Post-merge export complete")

        upload_result = self.nextcloud_client.upload_files(
            excel_path=sync_context.excel_path,
            text_path=sync_context.text_path,
            config=sync_context.config,
        )

        self.logger.info("Upload complete | result=%s", upload_result)

        self.sync_state_store.update_sync_state(
            sync_context.sync_state_file,
            {
                "imported_counts": imported_counts,
                "imported_movements": imported_movements,
                "uploaded": upload_result,
            },
        )

        duration = round(time.time() - start_time, 2)
        self.logger.info(
            "Sync finished | duration=%.2fs imported_counts=%s imported_movements=%s remote_counts=%s remote_movements=%s",
            duration,
            imported_counts,
            imported_movements,
            remote_count_counts,
            remote_count_movements,
        )

        return SyncResult(
            imported_counts=imported_counts,
            imported_movements=imported_movements,
            uploaded=upload_result,
            backup=str(backup_file),
            duration_seconds=duration,
        )

    def _cash_activity_count(self, sync_context: CashSyncContext) -> int:
        storage = self._storage_for(sync_context)
        return storage.get_row_count("cash_counts") + storage.get_row_count("cash_movements")

    def _set_balances_from_latest_counts(self, sync_context: CashSyncContext):
        storage = self._storage_for(sync_context)
        latest_counts_by_account = {}
        for count in storage.fetch_all_cash_counts():
            account_id = count.get("cash_account_id")
            if account_id:
                latest_counts_by_account[account_id] = count

        for account_id, count in latest_counts_by_account.items():
            storage.set_cash_account_balance_cents(
                account_id=account_id,
                balance_cents=int(count["total_cents"]),
            )

    def _record_bootstrap_check(
        self,
        sync_context: CashSyncContext,
        result: RemoteBootstrapResult,
    ):
        payload = {
            **result.to_dict(),
            "status": "skipped" if result.skipped else "imported",
            "checked_at": now_iso(),
            "mode": getattr(sync_context.config, "MODE", ""),
        }
        updates = {"bootstrap_last_check": payload}
        if not result.skipped:
            updates["bootstrap_last_import"] = payload
            updates.update(
                {
                    "bootstrap_imported_counts": result.imported_counts,
                    "bootstrap_imported_movements": result.imported_movements,
                    "bootstrap_source_format": result.source_format,
                }
            )

        self.sync_state_store.update_sync_state(sync_context.sync_state_file, updates)

    def bootstrap_remote_import_if_empty(
        self,
        sync_context: CashSyncContext | None = None,
    ) -> RemoteBootstrapResult:
        sync_context = self._context(sync_context)
        storage = self._storage_for(sync_context)
        if getattr(sync_context.config, "MODE", "") != "production":
            return RemoteBootstrapResult(
                imported_counts=0,
                imported_movements=0,
                source_format="",
                skipped=True,
                reason="not_production",
            )

        if self._cash_activity_count(sync_context) > 0:
            result = RemoteBootstrapResult(
                imported_counts=0,
                imported_movements=0,
                source_format="",
                skipped=True,
                reason="database_not_empty",
            )
            self._record_bootstrap_check(sync_context, result)
            return result

        remote_exists = self.nextcloud_client.download_remote_excel_if_exists(
            local_excel_path=sync_context.excel_path,
            config=sync_context.config,
        )
        if not remote_exists:
            result = RemoteBootstrapResult(
                imported_counts=0,
                imported_movements=0,
                source_format="",
                skipped=True,
                reason="remote_missing",
            )
            self._record_bootstrap_check(sync_context, result)
            return result

        remote_data = self.export_service.import_all_from_excel(sync_context.excel_path)
        source_format = str(remote_data.get("source_format") or "")

        accounts_result = storage.merge_imported_cash_accounts_append_only(
            imported_accounts=remote_data.get("cash_accounts", []),
        )
        contexts_result = storage.merge_imported_cash_contexts_append_only(
            imported_contexts=remote_data.get("cash_contexts", []),
        )
        counts_result = storage.merge_imported_cash_counts_append_only(
            imported_counts=remote_data.get("cash_counts", []),
        )
        movements_result = storage.merge_imported_cash_movements_append_only(
            imported_movements=remote_data.get("cash_movements", []),
        )

        imported_counts = counts_result["imported"]
        imported_movements = movements_result["imported"]

        if imported_counts and not remote_data.get("cash_movements"):
            self._set_balances_from_latest_counts(sync_context)

        self.export_service.export_all(
            db_path=sync_context.db_path,
            excel_path=sync_context.excel_path,
            text_path=sync_context.text_path,
        )

        self.logger.info(
            "Remote bootstrap import finished | source=%s accounts=%s contexts=%s "
            "counts=%s movements=%s",
            source_format,
            accounts_result["imported"],
            contexts_result["imported"],
            imported_counts,
            imported_movements,
        )

        result = RemoteBootstrapResult(
            imported_counts=imported_counts,
            imported_movements=imported_movements,
            source_format=source_format,
            skipped=False,
        )
        self._record_bootstrap_check(sync_context, result)
        return result

    def rebuild_exports(
        self,
        sync_context: CashSyncContext | None = None,
    ) -> SyncResult:
        self.logger.info("Manual rebuild + sync triggered")
        return self.run_full_sync_pipeline(sync_context)
