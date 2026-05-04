import logging
import time
from pathlib import Path

from core import export_utils
from core import nextcloud_sync
from core import storage
from core import sync_state

logger = logging.getLogger(__name__)


class CashService:
    def __init__(
        self,
        *,
        storage_repo=storage,
        export_service=export_utils,
        nextcloud_client=nextcloud_sync,
        sync_state_store=sync_state,
    ):
        self.storage = storage_repo
        self.export_service = export_service
        self.nextcloud_client = nextcloud_client
        self.sync_state_store = sync_state_store
        self.logger = logger

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

    def _run_full_sync_pipeline(
        self,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        backup_dir: Path,
        sync_state_file: Path,
        config,
    ):
        start_time = time.time()
        self.logger.info("Sync pipeline started | db=%s", db_path)

        backup_file = self.storage.create_backup(db_path, backup_dir)
        self.logger.info("Backup created | file=%s", backup_file)

        self.export_service.export_all(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
        )
        self.logger.info(
            "Local export complete | excel=%s text=%s",
            excel_path,
            text_path,
        )

        remote_exists = self.nextcloud_client.download_remote_excel_if_exists(
            local_excel_path=excel_path,
            config=config,
        )

        imported_counts = 0
        imported_movements = 0
        remote_count_counts = 0
        remote_count_movements = 0

        if remote_exists:
            self.logger.info("Remote Excel found, starting import")

            remote_data = self.export_service.import_all_from_excel(excel_path)
            remote_count_counts = len(remote_data.get("cash_counts", []))
            remote_count_movements = len(remote_data.get("cash_movements", []))

            self.logger.info(
                "Remote data loaded | counts=%s movements=%s",
                remote_count_counts,
                remote_count_movements,
            )
            accounts_result = self.storage.merge_imported_cash_accounts_append_only(
                db_path=db_path,
                imported_accounts=remote_data.get("cash_accounts", []),
            )

            contexts_result = self.storage.merge_imported_cash_contexts_append_only(
                db_path=db_path,
                imported_contexts=remote_data.get("cash_contexts", []),
            )

            counts_result = self.storage.merge_imported_cash_counts_append_only(
                db_path=db_path,
                imported_counts=remote_data.get("cash_counts", []),
            )

            movements_result = self.storage.merge_imported_cash_movements_append_only(
                db_path=db_path,
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
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
        )
        self.logger.info("Post-merge export complete")

        upload_result = self.nextcloud_client.upload_files(
            excel_path=excel_path,
            text_path=text_path,
            config=config,
        )

        self.logger.info("Upload complete | result=%s", upload_result)

        self.sync_state_store.update_sync_state(
            sync_state_file,
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

        return {
            "imported_counts": imported_counts,
            "imported_movements": imported_movements,
            "uploaded": upload_result,
            "backup": str(backup_file),
            "duration_seconds": duration,
        }

    def record_cash_count_and_sync(
        self,
        *,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        backup_dir: Path,
        sync_state_file: Path,
        config,
        cash_account_id: str,
        counted_by: str,
        total_cents: int,
        count_type: str,
        context_label: str = "",
        note: str = "",
        denominations: dict | None = None,
    ):
        self.logger.info(
            "Recording cash count | account=%s counted_by=%s total_cents=%s type=%s context=%s",
            cash_account_id,
            counted_by,
            total_cents,
            count_type,
            context_label,
        )

        self._validate_count(total_cents, denominations)

        if denominations:
            denoms = {k: v for k, v in denominations.items() if v not in (None, 0, "")}
            if denoms:
                self.logger.debug("Count denominations | %s", denoms)

        count_id = self.storage.create_cash_count(
            db_path=db_path,
            cash_account_id=cash_account_id,
            counted_by=counted_by,
            total_cents=total_cents,
            count_type=count_type,
            context_label=context_label,
            note=note,
            denominations=denominations,
        )

        self.storage.set_cash_account_balance_cents(
            db_path=db_path,
            account_id=cash_account_id,
            balance_cents=total_cents,
        )

        self.logger.info(
            "Cash count saved and account balance updated | id=%s account=%s balance_cents=%s",
            count_id,
            cash_account_id,
            total_cents,
        )

        sync_result = self._run_full_sync_pipeline(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
            backup_dir=backup_dir,
            sync_state_file=sync_state_file,
            config=config,
        )

        return {
            "count_id": count_id,
            **sync_result,
        }

    def record_cash_movement_and_sync(
        self,
        *,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        backup_dir: Path,
        sync_state_file: Path,
        config,
        from_account_id: str | None = None,
        to_account_id: str | None = None,
        amount_cents: int,
        context_label: str = "",
        actor: str = "",
        reference: str = "",
        note: str = "",
        denominations: dict | None = None,
    ):
        self.logger.info(
            "Recording cash movement | amount=%s from=%s to=%s context=%s",
            amount_cents,
            from_account_id,
            to_account_id,
            context_label,
        )

        self._validate_movement(
            amount_cents,
            from_account_id,
            to_account_id,
            denominations,
        )

        movement_id = self.storage.create_cash_movement(
            db_path=db_path,
            amount_cents=amount_cents,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            context_label=context_label,
            actor=actor,
            reference=reference,
            note=note,
            denominations=denominations,
        )

        if from_account_id:
            self.storage.adjust_cash_account_balance_cents(
                db_path=db_path,
                account_id=from_account_id,
                delta_cents=-amount_cents,
            )

        if to_account_id:
            self.storage.adjust_cash_account_balance_cents(
                db_path=db_path,
                account_id=to_account_id,
                delta_cents=amount_cents,
            )

        self.logger.info(
            "Cash movement saved and balances updated | id=%s from=%s to=%s amount_cents=%s",
            movement_id,
            from_account_id,
            to_account_id,
            amount_cents,
        )

        auto_return_result = None

        try:
            runner_account = self.storage.fetch_cash_account_by_name(
                db_path,
                "Runner Float",
            )
            supplier_account = self.storage.fetch_cash_account_by_name(
                db_path,
                "Supplier / Drinks Purchase",
            )

            if (
                runner_account
                and supplier_account
                and from_account_id == runner_account["id"]
                and to_account_id == supplier_account["id"]
            ):
                auto_return_result = self._maybe_auto_return_runner_change(
                    db_path=db_path,
                    context_label=context_label,
                    actor=actor,
                    reference=reference,
                )
        except Exception:
            self.logger.exception("Failed during automatic runner change return")
            raise

        sync_result = self._run_full_sync_pipeline(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
            backup_dir=backup_dir,
            sync_state_file=sync_state_file,
            config=config,
        )

        return {
            "movement_id": movement_id,
            "auto_return": auto_return_result,
            **sync_result,
        }

    def _maybe_auto_return_runner_change(
        self,
        *,
        db_path: Path,
        context_label: str,
        actor: str,
        reference: str,
    ):
        """
        Business rule:
        After a supplier purchase from Runner Float, automatically return any
        remaining Runner Float balance back to Bar Cash Box.
        """
        runner_account = self.storage.require_cash_account_by_name(
            db_path,
            "Runner Float",
        )
        bar_account = self.storage.require_cash_account_by_name(db_path, "Bar Cash Box")

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

        auto_movement_id = self.storage.create_cash_movement(
            db_path=db_path,
            from_account_id=runner_account["id"],
            to_account_id=bar_account["id"],
            amount_cents=runner_balance_cents,
            context_label=context_label,
            actor=actor,
            reference=reference,
            note="Auto-return of remaining runner float after supplier purchase",
            denominations=None,
        )

        self.storage.adjust_cash_account_balance_cents(
            db_path=db_path,
            account_id=runner_account["id"],
            delta_cents=-runner_balance_cents,
        )
        self.storage.adjust_cash_account_balance_cents(
            db_path=db_path,
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

    def rebuild_exports_and_sync(
        self,
        *,
        db_path: Path,
        excel_path: Path,
        text_path: Path,
        backup_dir: Path,
        sync_state_file: Path,
        config,
    ):
        self.logger.info("Manual rebuild + sync triggered")
        return self._run_full_sync_pipeline(
            db_path=db_path,
            excel_path=excel_path,
            text_path=text_path,
            backup_dir=backup_dir,
            sync_state_file=sync_state_file,
            config=config,
        )


_default_cash_service = CashService()


def _validate_movement(
    amount_cents: int,
    from_account_id: str | None,
    to_account_id: str | None,
    denominations: dict | None = None,
):
    return _default_cash_service._validate_movement(
        amount_cents,
        from_account_id,
        to_account_id,
        denominations,
    )


def _validate_count(
    total_cents: int,
    denominations: dict | None,
):
    return _default_cash_service._validate_count(total_cents, denominations)


def _run_full_sync_pipeline(
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
):
    return _default_cash_service._run_full_sync_pipeline(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )


def record_cash_count_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
    cash_account_id: str,
    counted_by: str,
    total_cents: int,
    count_type: str,
    context_label: str = "",
    note: str = "",
    denominations: dict | None = None,
):
    return _default_cash_service.record_cash_count_and_sync(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
        cash_account_id=cash_account_id,
        counted_by=counted_by,
        total_cents=total_cents,
        count_type=count_type,
        context_label=context_label,
        note=note,
        denominations=denominations,
    )


def record_cash_movement_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
    from_account_id: str | None = None,
    to_account_id: str | None = None,
    amount_cents: int,
    context_label: str = "",
    actor: str = "",
    reference: str = "",
    note: str = "",
    denominations: dict | None = None,
):
    return _default_cash_service.record_cash_movement_and_sync(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        amount_cents=amount_cents,
        context_label=context_label,
        actor=actor,
        reference=reference,
        note=note,
        denominations=denominations,
    )


def _maybe_auto_return_runner_change(
    *,
    db_path: Path,
    context_label: str,
    actor: str,
    reference: str,
):
    return _default_cash_service._maybe_auto_return_runner_change(
        db_path=db_path,
        context_label=context_label,
        actor=actor,
        reference=reference,
    )


def rebuild_exports_and_sync(
    *,
    db_path: Path,
    excel_path: Path,
    text_path: Path,
    backup_dir: Path,
    sync_state_file: Path,
    config,
):
    return _default_cash_service.rebuild_exports_and_sync(
        db_path=db_path,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config,
    )
