import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core import export_utils, nextcloud_sync, storage, sync_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CashSyncContext:
    db_path: Path
    excel_path: Path
    text_path: Path
    backup_dir: Path
    sync_state_file: Path
    config: Any


@dataclass(frozen=True)
class CashCountRequest:
    cash_account_id: str
    counted_by: str
    total_cents: int
    count_type: str
    context_label: str = ""
    note: str = ""
    denominations: dict | None = None


@dataclass(frozen=True)
class CashMovementRequest:
    amount_cents: int
    from_account_id: str | None = None
    to_account_id: str | None = None
    context_label: str = ""
    actor: str = ""
    reference: str = ""
    note: str = ""
    denominations: dict | None = None


@dataclass(frozen=True)
class SyncResult:
    imported_counts: int
    imported_movements: int
    uploaded: dict
    backup: str
    duration_seconds: float

    def to_dict(self) -> dict:
        return {
            "imported_counts": self.imported_counts,
            "imported_movements": self.imported_movements,
            "uploaded": self.uploaded,
            "backup": self.backup,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class CashCountResult:
    count_id: str
    sync: SyncResult

    def to_dict(self) -> dict:
        return {
            "count_id": self.count_id,
            **self.sync.to_dict(),
        }


@dataclass(frozen=True)
class CashMovementResult:
    movement_id: str
    auto_return: dict | None
    sync: SyncResult

    def to_dict(self) -> dict:
        return {
            "movement_id": self.movement_id,
            "auto_return": self.auto_return,
            **self.sync.to_dict(),
        }


class CashService:
    def __init__(
        self,
        *,
        storage_repo=storage,
        export_service=export_utils,
        nextcloud_client=nextcloud_sync,
        sync_state_store=sync_state,
        sync_context: CashSyncContext | None = None,
    ):
        self.storage = storage_repo
        self.export_service = export_service
        self.nextcloud_client = nextcloud_client
        self.sync_state_store = sync_state_store
        self.sync_context = sync_context
        self.logger = logger

    def configure_sync_context(self, sync_context: CashSyncContext):
        self.sync_context = sync_context

    def _context(self, sync_context: CashSyncContext | None = None) -> CashSyncContext:
        resolved = sync_context or self.sync_context
        if resolved is None:
            raise ValueError("CashSyncContext is required")

        return resolved

    def _storage_has_bound_db(self) -> bool:
        return bool(getattr(self.storage, "db_path", None))

    def _storage_call(
        self,
        method_name: str,
        sync_context: CashSyncContext,
        *args,
        **kwargs,
    ):
        method = getattr(self.storage, method_name)
        if self._storage_has_bound_db():
            return method(*args, **kwargs)

        return method(*args, db_path=sync_context.db_path, **kwargs)

    def _validate_movement(
        self,
        amount_cents: int,
        from_account_id: str | None,
        to_account_id: str | None,
        denominations: dict | None = None,
    ):
        if amount_cents <= 0:
            raise ValueError("Amount must be > 0")

        if not from_account_id and not to_account_id:
            raise ValueError("Movement must have at least a source or target account")

        if from_account_id and to_account_id and from_account_id == to_account_id:
            raise ValueError("Source and target account cannot be the same")

        if denominations:
            calc = self.storage.calculate_total_cents_from_denominations(denominations)
            if calc != amount_cents:
                self.logger.warning(
                    "Movement denomination mismatch | calculated=%s total=%s difference=%s",
                    calc,
                    amount_cents,
                    amount_cents - calc,
                )

    def _validate_count(
        self,
        total_cents: int,
        denominations: dict | None,
    ):
        if total_cents < 0:
            raise ValueError("Count total cannot be negative")

        if denominations:
            calc = self.storage.calculate_total_cents_from_denominations(denominations)
            if calc != total_cents:
                self.logger.warning(
                    "Denomination mismatch | calculated=%s total=%s difference=%s",
                    calc,
                    total_cents,
                    total_cents - calc,
                )

    def _run_full_sync_pipeline(self, sync_context: CashSyncContext | None = None):
        sync_context = self._context(sync_context)
        start_time = time.time()
        self.logger.info("Sync pipeline started | db=%s", sync_context.db_path)

        backup_file = self._storage_call(
            "create_backup",
            sync_context,
            backup_dir=sync_context.backup_dir,
        )
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
            accounts_result = self._storage_call(
                "merge_imported_cash_accounts_append_only",
                sync_context,
                imported_accounts=remote_data.get("cash_accounts", []),
            )

            contexts_result = self._storage_call(
                "merge_imported_cash_contexts_append_only",
                sync_context,
                imported_contexts=remote_data.get("cash_contexts", []),
            )

            counts_result = self._storage_call(
                "merge_imported_cash_counts_append_only",
                sync_context,
                imported_counts=remote_data.get("cash_counts", []),
            )

            movements_result = self._storage_call(
                "merge_imported_cash_movements_append_only",
                sync_context,
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

    def record_count(
        self,
        request: CashCountRequest,
        sync_context: CashSyncContext | None = None,
    ) -> CashCountResult:
        sync_context = self._context(sync_context)
        self.logger.info(
            "Recording cash count | account=%s counted_by=%s total_cents=%s type=%s context=%s",
            request.cash_account_id,
            request.counted_by,
            request.total_cents,
            request.count_type,
            request.context_label,
        )

        self._validate_count(request.total_cents, request.denominations)

        if request.denominations:
            denoms = {k: v for k, v in request.denominations.items() if v not in (None, 0, "")}
            if denoms:
                self.logger.debug("Count denominations | %s", denoms)

        count_id = self._storage_call(
            "create_cash_count",
            sync_context,
            cash_account_id=request.cash_account_id,
            counted_by=request.counted_by,
            total_cents=request.total_cents,
            count_type=request.count_type,
            context_label=request.context_label,
            note=request.note,
            denominations=request.denominations,
        )

        self._storage_call(
            "set_cash_account_balance_cents",
            sync_context,
            account_id=request.cash_account_id,
            balance_cents=request.total_cents,
        )

        self.logger.info(
            "Cash count saved and account balance updated | id=%s account=%s balance_cents=%s",
            count_id,
            request.cash_account_id,
            request.total_cents,
        )

        return CashCountResult(
            count_id=count_id,
            sync=self._run_full_sync_pipeline(sync_context),
        )

    def record_movement(
        self,
        request: CashMovementRequest,
        sync_context: CashSyncContext | None = None,
    ) -> CashMovementResult:
        sync_context = self._context(sync_context)
        self.logger.info(
            "Recording cash movement | amount=%s from=%s to=%s context=%s",
            request.amount_cents,
            request.from_account_id,
            request.to_account_id,
            request.context_label,
        )

        self._validate_movement(
            request.amount_cents,
            request.from_account_id,
            request.to_account_id,
            request.denominations,
        )

        movement_id = self._storage_call(
            "create_cash_movement",
            sync_context,
            amount_cents=request.amount_cents,
            from_account_id=request.from_account_id,
            to_account_id=request.to_account_id,
            context_label=request.context_label,
            actor=request.actor,
            reference=request.reference,
            note=request.note,
            denominations=request.denominations,
        )

        if request.from_account_id:
            self._storage_call(
                "adjust_cash_account_balance_cents",
                sync_context,
                account_id=request.from_account_id,
                delta_cents=-request.amount_cents,
            )

        if request.to_account_id:
            self._storage_call(
                "adjust_cash_account_balance_cents",
                sync_context,
                account_id=request.to_account_id,
                delta_cents=request.amount_cents,
            )

        self.logger.info(
            "Cash movement saved and balances updated | id=%s from=%s to=%s amount_cents=%s",
            movement_id,
            request.from_account_id,
            request.to_account_id,
            request.amount_cents,
        )

        auto_return_result = None

        try:
            runner_account = self._storage_call(
                "fetch_cash_account_by_name",
                sync_context,
                name="Runner Float",
            )
            supplier_account = self._storage_call(
                "fetch_cash_account_by_name",
                sync_context,
                name="Supplier / Drinks Purchase",
            )

            if (
                runner_account
                and supplier_account
                and request.from_account_id == runner_account["id"]
                and request.to_account_id == supplier_account["id"]
            ):
                auto_return_result = self._maybe_auto_return_runner_change(
                    sync_context=sync_context,
                    context_label=request.context_label,
                    actor=request.actor,
                    reference=request.reference,
                )
        except Exception:
            self.logger.exception("Failed during automatic runner change return")
            raise

        return CashMovementResult(
            movement_id=movement_id,
            auto_return=auto_return_result,
            sync=self._run_full_sync_pipeline(sync_context),
        )

    def _maybe_auto_return_runner_change(
        self,
        *,
        sync_context: CashSyncContext | None = None,
        context_label: str,
        actor: str,
        reference: str,
    ):
        """
        Business rule:
        After a supplier purchase from Runner Float, automatically return any
        remaining Runner Float balance back to Bar Cash Box.
        """
        sync_context = self._context(sync_context)

        runner_account = self._storage_call(
            "require_cash_account_by_name",
            sync_context,
            name="Runner Float",
        )
        bar_account = self._storage_call(
            "require_cash_account_by_name",
            sync_context,
            name="Bar Cash Box",
        )

        runner_balance_cents = int(runner_account.get("current_balance_cents") or 0)

        if runner_balance_cents <= 0:
            self.logger.info(
                "No runner change to return | runner_balance_cents=%s",
                runner_balance_cents,
            )
            return None

        self.logger.info(
            "Auto-returning runner change | amount_cents=%s",
            runner_balance_cents,
        )

        auto_movement_id = self._storage_call(
            "create_cash_movement",
            sync_context,
            from_account_id=runner_account["id"],
            to_account_id=bar_account["id"],
            amount_cents=runner_balance_cents,
            context_label=context_label,
            actor=actor,
            reference=reference,
            note="Auto-return of remaining runner float after supplier purchase",
            denominations=None,
        )

        self._storage_call(
            "adjust_cash_account_balance_cents",
            sync_context,
            account_id=runner_account["id"],
            delta_cents=-runner_balance_cents,
        )
        self._storage_call(
            "adjust_cash_account_balance_cents",
            sync_context,
            account_id=bar_account["id"],
            delta_cents=runner_balance_cents,
        )

        self.logger.info(
            "Auto-return movement created | id=%s from=%s to=%s amount_cents=%s",
            auto_movement_id,
            runner_account["id"],
            bar_account["id"],
            runner_balance_cents,
        )

        return {
            "movement_id": auto_movement_id,
            "amount_cents": runner_balance_cents,
        }

    def rebuild_exports(
        self,
        sync_context: CashSyncContext | None = None,
    ) -> SyncResult:
        self.logger.info("Manual rebuild + sync triggered")
        return self._run_full_sync_pipeline(sync_context)
