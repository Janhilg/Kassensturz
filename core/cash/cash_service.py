import logging

from core.cash.cash_count_request import CashCountRequest
from core.cash.cash_count_result import CashCountResult
from core.cash.cash_movement_request import CashMovementRequest
from core.cash.cash_movement_result import CashMovementResult
from core.cash.cash_service_storage import CashServiceStorage
from core.cash.cash_sync_context import CashSyncContext
from core.cash.cash_sync_service import CashSyncService
from core.cash.remote_bootstrap_result import RemoteBootstrapResult
from core.cash.sync_result import SyncResult
from core.storage_objects.cash_storage import CashStorage

logger = logging.getLogger(__name__)


class CashService:
    def __init__(
        self,
        *,
        storage_repo=None,
        sync_service: CashSyncService | None = None,
        export_service=None,
        nextcloud_client=None,
        sync_state_store=None,
        sync_context: CashSyncContext | None = None,
    ):
        self.storage = storage_repo if storage_repo is not None else CashStorage()
        self.sync_service = (
            sync_service
            if sync_service is not None
            else CashSyncService(
                storage_repo=self.storage,
                export_service=export_service,
                nextcloud_client=nextcloud_client,
                sync_state_store=sync_state_store,
                sync_context=sync_context,
            )
        )
        self.sync_context = sync_context
        self.logger = logger

    def configure_sync_context(self, sync_context: CashSyncContext):
        self.sync_context = sync_context
        self.sync_service.configure_sync_context(sync_context)

    def _context(self, sync_context: CashSyncContext | None = None) -> CashSyncContext:
        resolved = sync_context or self.sync_context
        if resolved is None:
            raise ValueError("CashSyncContext is required")

        return resolved

    def _storage_for(self, sync_context: CashSyncContext) -> CashServiceStorage:
        return CashServiceStorage(self.storage, sync_context)

    def _validate_movement(
        self,
        amount_cents: int,
        from_account_id: str | None,
        to_account_id: str | None,
        storage: CashServiceStorage,
        denominations: dict | None = None,
    ):
        if amount_cents <= 0:
            raise ValueError("Amount must be > 0")

        if not from_account_id and not to_account_id:
            raise ValueError("Movement must have at least a source or target account")

        if from_account_id and to_account_id and from_account_id == to_account_id:
            raise ValueError("Source and target account cannot be the same")

        if denominations:
            calc = storage.calculate_total_cents_from_denominations(denominations)
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
        storage: CashServiceStorage,
        denominations: dict | None,
    ):
        if total_cents < 0:
            raise ValueError("Count total cannot be negative")

        if denominations:
            calc = storage.calculate_total_cents_from_denominations(denominations)
            if calc != total_cents:
                self.logger.warning(
                    "Denomination mismatch | calculated=%s total=%s difference=%s",
                    calc,
                    total_cents,
                    total_cents - calc,
                )

    def bootstrap_remote_import_if_empty(
        self,
        sync_context: CashSyncContext | None = None,
    ) -> RemoteBootstrapResult:
        return self.sync_service.bootstrap_remote_import_if_empty(self._context(sync_context))

    def record_count(
        self,
        request: CashCountRequest,
        sync_context: CashSyncContext | None = None,
    ) -> CashCountResult:
        sync_context = self._context(sync_context)
        storage = self._storage_for(sync_context)
        self.logger.info(
            "Recording cash count | account=%s counted_by=%s total_cents=%s type=%s context=%s",
            request.cash_account_id,
            request.counted_by,
            request.total_cents,
            request.count_type,
            request.context_label,
        )

        self._validate_count(request.total_cents, storage, request.denominations)

        if request.denominations:
            denoms = {
                key: value
                for key, value in request.denominations.items()
                if value not in (None, 0, "")
            }
            if denoms:
                self.logger.debug("Count denominations | %s", denoms)

        count_id = storage.create_cash_count(
            cash_account_id=request.cash_account_id,
            counted_by=request.counted_by,
            total_cents=request.total_cents,
            count_type=request.count_type,
            context_label=request.context_label,
            note=request.note,
            denominations=request.denominations,
        )

        storage.set_cash_account_balance_cents(
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
            sync=self.sync_service.run_full_sync_pipeline(sync_context),
        )

    def record_movement(
        self,
        request: CashMovementRequest,
        sync_context: CashSyncContext | None = None,
    ) -> CashMovementResult:
        sync_context = self._context(sync_context)
        storage = self._storage_for(sync_context)
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
            storage,
            request.denominations,
        )

        movement_id = storage.create_cash_movement(
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
            storage.adjust_cash_account_balance_cents(
                account_id=request.from_account_id,
                delta_cents=-request.amount_cents,
            )

        if request.to_account_id:
            storage.adjust_cash_account_balance_cents(
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
            runner_account = storage.fetch_cash_account_by_name("Runner Float")
            supplier_account = storage.fetch_cash_account_by_name("Supplier / Drinks Purchase")

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
            sync=self.sync_service.run_full_sync_pipeline(sync_context),
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
        storage = self._storage_for(sync_context)

        runner_account = storage.require_cash_account_by_name("Runner Float")
        bar_account = storage.require_cash_account_by_name("Bar Cash Box")

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

        auto_movement_id = storage.create_cash_movement(
            from_account_id=runner_account["id"],
            to_account_id=bar_account["id"],
            amount_cents=runner_balance_cents,
            context_label=context_label,
            actor=actor,
            reference=reference,
            note="Auto-return of remaining runner float after supplier purchase",
            denominations=None,
        )

        storage.adjust_cash_account_balance_cents(
            account_id=runner_account["id"],
            delta_cents=-runner_balance_cents,
        )
        storage.adjust_cash_account_balance_cents(
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
        return self.sync_service.rebuild_exports(self._context(sync_context))
