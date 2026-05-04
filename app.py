import logging
import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from config import Config
from core import storage, sync_state
from core.cash_service import (
    CashCountRequest,
    CashMovementRequest,
    CashService,
    CashSyncContext,
)
from core.export_utils import CashExportService
from core.logging_config import setup_logging
from core.nextcloud_sync import NextcloudClient

mimetypes.add_type("application/javascript", ".js")

logger = logging.getLogger(__name__)


def _default_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


@dataclass
class AppPaths:
    base_dir: Path
    data_dir: Path
    backup_dir: Path
    db_file: Path
    excel_export_file: Path
    text_export_file: Path
    sync_state_file: Path

    @classmethod
    def from_config(cls, config, base_dir: Path):
        data_dir = base_dir / "data" / config.MODE
        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            backup_dir=data_dir / "backups",
            db_file=data_dir / "kassensturz.db",
            excel_export_file=data_dir / "kassensturz_data.xlsx",
            text_export_file=data_dir / "kassensturz_data.txt",
            sync_state_file=data_dir / "sync_state.json",
        )

    @classmethod
    def from_files(
        cls,
        *,
        base_dir: Path,
        db_file: Path,
        excel_export_file: Path,
        text_export_file: Path,
        backup_dir: Path,
        sync_state_file: Path,
    ):
        return cls(
            base_dir=base_dir,
            data_dir=db_file.parent,
            backup_dir=backup_dir,
            db_file=db_file,
            excel_export_file=excel_export_file,
            text_export_file=text_export_file,
            sync_state_file=sync_state_file,
        )


class KassensturzWebApp:
    def __init__(
        self,
        *,
        config=Config,
        base_dir: Path | None = None,
        paths: AppPaths | None = None,
    ):
        self.config = config
        self.paths = paths or AppPaths.from_config(
            config=config,
            base_dir=base_dir or _default_base_dir(),
        )
        self._configure_services()

        setup_logging(self.paths.base_dir, debug=(self.config.MODE == "debug"))
        self.logger = logging.getLogger(__name__)

        self.flask_app = self._create_flask_app()
        self._register_routes()
        self.initialize_storage()

    def _sync_context(self) -> CashSyncContext:
        return CashSyncContext(
            db_path=self.paths.db_file,
            excel_path=self.paths.excel_export_file,
            text_path=self.paths.text_export_file,
            backup_dir=self.paths.backup_dir,
            sync_state_file=self.paths.sync_state_file,
            config=self.config,
        )

    def _configure_services(self):
        self.storage = storage.CashStorage(self.paths.db_file)
        self.sync_state = sync_state.SyncStateStore()
        self.export_service = CashExportService()
        self.nextcloud_client = NextcloudClient()
        self.cash_service = CashService(
            storage_repo=self.storage,
            export_service=self.export_service,
            nextcloud_client=self.nextcloud_client,
            sync_state_store=self.sync_state,
            sync_context=self._sync_context(),
        )

    def _create_flask_app(self) -> Flask:
        flask_app = Flask(__name__)
        flask_app.config.from_object(self.config)
        flask_app.secret_key = self.config.SECRET_KEY
        return flask_app

    def _register_routes(self):
        self.flask_app.context_processor(self.inject_global_template_vars)

        self.flask_app.add_url_rule(
            "/",
            endpoint="index",
            view_func=self.index,
            methods=["GET", "POST"],
        )
        self.flask_app.add_url_rule(
            "/cash/movement",
            endpoint="cash_movement",
            view_func=self.cash_movement,
            methods=["GET", "POST"],
        )
        self.flask_app.add_url_rule(
            "/balances",
            endpoint="balances",
            view_func=self.balances,
        )
        self.flask_app.add_url_rule(
            "/admin/login",
            endpoint="admin_login",
            view_func=self.admin_login,
            methods=["GET", "POST"],
        )
        self.flask_app.add_url_rule(
            "/admin/logout",
            endpoint="admin_logout",
            view_func=self.admin_logout,
        )
        self.flask_app.add_url_rule(
            "/admin",
            endpoint="admin_dashboard",
            view_func=self.admin_dashboard,
        )
        self.flask_app.add_url_rule(
            "/admin/restore-backup",
            endpoint="admin_restore_backup",
            view_func=self.admin_restore_backup,
            methods=["POST"],
        )
        self.flask_app.add_url_rule(
            "/admin/rebuild-exports",
            endpoint="admin_rebuild_exports",
            view_func=self.admin_rebuild_exports,
            methods=["POST"],
        )
        self.flask_app.add_url_rule(
            "/admin/sync-now",
            endpoint="admin_sync_now",
            view_func=self.admin_sync_now,
            methods=["POST"],
        )

    def initialize_storage(self):
        self.storage.ensure_db_file()
        self.storage.seed_default_cash_accounts()
        self.logger.info(
            "App startup | mode=%s db=%s",
            self.config.MODE,
            self.paths.db_file,
        )

    def configure_paths(self, paths: AppPaths, *, initialize: bool = True):
        self.paths = paths
        _sync_legacy_path_globals(paths)
        self._configure_services()
        if initialize:
            self.initialize_storage()

    def record_cash_count(self, count_request: CashCountRequest):
        return self.cash_service.record_count(count_request)

    def record_cash_movement(self, movement_request: CashMovementRequest):
        return self.cash_service.record_movement(movement_request)

    def rebuild_exports(self):
        return self.cash_service.rebuild_exports()

    def _result_dict(self, result) -> dict:
        if hasattr(result, "to_dict"):
            return result.to_dict()

        return dict(result)

    def inject_global_template_vars(self):
        return {
            "mode": self.config.MODE,
            "config": self.config,
        }

    def _admin_redirect_if_needed(self):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return None

    def _parse_cents_from_form_amount(self, raw_value: str) -> int:
        raw_value = str(raw_value).strip().replace(",", ".")
        return self.storage.eur_to_cents(raw_value)

    def _get_denominations_from_request_form(self):
        return self.storage.get_denomination_values_from_form(request.form)

    def _account_translation_key(self, account: dict) -> str:
        name = str(account.get("name") or "")
        account_id = str(account.get("id") or "")

        if name.startswith("account_"):
            return name

        if account_id.startswith("acc_"):
            return f"account_{account_id.removeprefix('acc_')}"

        return name

    def _with_account_translation_keys(self, accounts: list[dict]) -> list[dict]:
        return [
            {
                **account,
                "i18n_key": self._account_translation_key(account),
            }
            for account in accounts
        ]

    def _group_accounts_for_select(self, accounts: list[dict]) -> list[dict]:
        groups = {
            self.config.ACCOUNT_TYPE_CASH_BOX: [],
            self.config.ACCOUNT_TYPE_FLOAT: [],
            self.config.ACCOUNT_TYPE_EXTERNAL_SINK: [],
            self.config.ACCOUNT_TYPE_BANK: [],
        }

        for account in accounts:
            account_type = account.get("account_type")
            if account_type in groups:
                groups[account_type].append(account)

        ordered = [
            {
                "type": self.config.ACCOUNT_TYPE_CASH_BOX,
                "accounts": groups[self.config.ACCOUNT_TYPE_CASH_BOX],
            },
            {
                "type": self.config.ACCOUNT_TYPE_FLOAT,
                "accounts": groups[self.config.ACCOUNT_TYPE_FLOAT],
            },
            {
                "type": self.config.ACCOUNT_TYPE_EXTERNAL_SINK,
                "accounts": groups[self.config.ACCOUNT_TYPE_EXTERNAL_SINK],
            },
            {
                "type": self.config.ACCOUNT_TYPE_BANK,
                "accounts": groups[self.config.ACCOUNT_TYPE_BANK],
            },
        ]

        return [group for group in ordered if group["accounts"]]

    def _common_template_context(self):
        cash_accounts = self._with_account_translation_keys(
            self.storage.fetch_all_cash_accounts(
                active_only=True,
            )
        )
        cash_box_accounts = self._with_account_translation_keys(
            self.storage.fetch_cash_accounts_by_type(
                self.config.ACCOUNT_TYPE_CASH_BOX,
                active_only=True,
            )
        )

        return {
            "cash_accounts": cash_accounts,
            "cash_box_accounts": cash_box_accounts,
            "grouped_cash_accounts": self._group_accounts_for_select(cash_accounts),
            "recent_contexts": self.storage.fetch_recent_cash_contexts(
                limit=20,
            ),
            "latest_context_label": self.storage.get_latest_cash_context_label(),
            "count_types": self.config.COUNT_TYPES,
            "denom_fields": self.storage.DENOM_FIELDS,
            "mode": self.config.MODE,
        }

    def index(self):
        if request.method == "POST":
            try:
                cash_account_id = request.form.get("cash_account_id", "").strip()
                counted_by = request.form.get("counted_by", "").strip()
                count_type = request.form.get("count_type", "").strip()
                context_label = request.form.get("context_label", "").strip()
                note = request.form.get("note", "").strip()

                denominations = self._get_denominations_from_request_form()

                raw_total = request.form.get("total_eur", "").strip()
                if raw_total:
                    total_cents = self._parse_cents_from_form_amount(raw_total)
                else:
                    total_cents = self.storage.calculate_total_cents_from_denominations(
                        denominations
                    )

                self.logger.info(
                    "Count form submitted | account=%s counted_by=%s type=%s context=%s",
                    cash_account_id,
                    counted_by,
                    count_type,
                    context_label,
                )

                result = self._result_dict(
                    self.record_cash_count(
                        CashCountRequest(
                            cash_account_id=cash_account_id,
                            counted_by=counted_by,
                            total_cents=total_cents,
                            count_type=count_type,
                            context_label=context_label,
                            note=note,
                            denominations=denominations,
                        )
                    )
                )

                flash(
                    (
                        f"Cash count recorded. "
                        f"Imported counts: {result['imported_counts']}, "
                        f"imported movements: {result['imported_movements']}."
                    ),
                    "count_success",
                )
                return redirect(url_for("index"))

            except Exception as exc:
                self.logger.exception("Failed to record cash count")
                flash(f"Failed to record cash count: {exc}", "error")

        context = self._common_template_context()
        context["recent_counts"] = self.storage.fetch_recent_cash_counts(
            limit=20,
        )
        return render_template("index.html", **context)

    def cash_movement(self):
        if request.method == "POST":
            try:
                from_account_id = request.form.get("from_account_id", "").strip() or None
                to_account_id = request.form.get("to_account_id", "").strip() or None
                actor = request.form.get("actor", "").strip()
                reference = request.form.get("reference", "").strip()
                note = request.form.get("note", "").strip()
                context_label = request.form.get("context_label", "").strip()
                amount_cents = self._parse_cents_from_form_amount(
                    request.form.get("amount_eur", "").strip()
                )

                self.logger.info(
                    "Movement form submitted | from=%s to=%s actor=%s context=%s",
                    from_account_id,
                    to_account_id,
                    actor,
                    context_label,
                )
                denominations = self._get_denominations_from_request_form()

                result = self._result_dict(
                    self.record_cash_movement(
                        CashMovementRequest(
                            amount_cents=amount_cents,
                            from_account_id=from_account_id,
                            to_account_id=to_account_id,
                            context_label=context_label,
                            actor=actor,
                            reference=reference,
                            note=note,
                            denominations=denominations,
                        )
                    )
                )

                message = (
                    f"Cash movement recorded. "
                    f"Imported counts: {result['imported_counts']}, "
                    f"imported movements: {result['imported_movements']}."
                )

                if result.get("auto_return"):
                    returned_eur = result["auto_return"]["amount_cents"] / 100
                    message += (
                        f" Auto-returned € {returned_eur:.2f} from Runner Float to Bar Cash Box."
                    )

                flash(message, "movement_success")
                return redirect(url_for("cash_movement"))

            except Exception as exc:
                self.logger.exception("Failed to record cash movement")
                flash(f"Failed to record cash movement: {exc}", "error")

        context = self._common_template_context()
        context["recent_movements"] = self.storage.fetch_recent_cash_movements(
            limit=20,
        )
        return render_template("cash_movement.html", **context)

    def balances(self):
        context = {
            **self._common_template_context(),
            "balances": self.storage.fetch_cash_account_balances(),
            "recent_counts": self.storage.fetch_recent_cash_counts(
                limit=4,
            ),
            "recent_movements": self.storage.fetch_recent_cash_movements(
                limit=4,
            ),
        }
        return render_template("balances.html", **context)

    def admin_login(self):
        if request.method == "POST":
            submitted_password = request.form.get("password", "")
            if submitted_password == self.config.ADMIN_PASSWORD:
                session["admin_logged_in"] = True

                return redirect(url_for("admin_dashboard"))

            flash("Invalid password.", "error")

        return render_template("admin_login.html")

    def admin_logout(self):
        session.pop("admin_logged_in", None)
        flash("Logged out.", "admin_success")
        return redirect(url_for("index"))

    def admin_dashboard(self):
        redirect_response = self._admin_redirect_if_needed()
        if redirect_response:
            return redirect_response

        context = {
            **self._common_template_context(),
            "available_backups": self.storage.list_backups(self.paths.backup_dir),
            "sync_state_data": self.sync_state.load_sync_state(self.paths.sync_state_file),
            "row_counts": {
                "cash_accounts": self.storage.get_row_count(
                    "cash_accounts",
                ),
                "cash_contexts": self.storage.get_row_count(
                    "cash_contexts",
                ),
                "cash_movements": self.storage.get_row_count(
                    "cash_movements",
                ),
                "cash_counts": self.storage.get_row_count(
                    "cash_counts",
                ),
            },
        }
        return render_template("admin.html", **context)

    def admin_restore_backup(self):
        redirect_response = self._admin_redirect_if_needed()
        if redirect_response:
            return redirect_response

        try:
            backup_name = request.form.get("backup_name", "").strip()
            if not backup_name:
                raise ValueError("No backup selected.")

            backup_file = self.paths.backup_dir / backup_name

            self.storage.restore_backup(
                backup_file=backup_file,
            )

            self.rebuild_exports()

            flash(f"Backup restored: {backup_name}", "admin_success")

        except Exception as exc:
            self.logger.exception("Backup restore failed")
            flash(f"Restore failed: {exc}", "error")

        return redirect(url_for("admin_dashboard"))

    def admin_rebuild_exports(self):
        redirect_response = self._admin_redirect_if_needed()
        if redirect_response:
            return redirect_response

        try:
            result = self._result_dict(self.rebuild_exports())
            flash(
                (
                    f"Rebuild + sync complete. "
                    f"Imported counts: {result['imported_counts']}, "
                    f"imported movements: {result['imported_movements']}."
                ),
                "admin_success",
            )
        except Exception as exc:
            self.logger.exception("Manual rebuild failed")
            flash(f"Rebuild failed: {exc}", "error")

        return redirect(url_for("admin_dashboard"))

    def admin_sync_now(self):
        redirect_response = self._admin_redirect_if_needed()
        if redirect_response:
            return redirect_response

        try:
            result = self._result_dict(self.rebuild_exports())
            flash(
                (
                    f"Sync complete. "
                    f"Imported counts: {result['imported_counts']}, "
                    f"imported movements: {result['imported_movements']}."
                ),
                "admin_success",
            )
        except Exception as exc:
            self.logger.exception("Manual sync failed")
            flash(f"Sync failed: {exc}", "error")

        return redirect(url_for("admin_dashboard"))


def _sync_legacy_path_globals(paths: AppPaths):
    globals()["BASE_DIR"] = paths.base_dir
    globals()["DATA_DIR"] = paths.data_dir
    globals()["BACKUP_DIR"] = paths.backup_dir
    globals()["LOCAL_DB_FILE"] = paths.db_file
    globals()["LOCAL_EXCEL_EXPORT_FILE"] = paths.excel_export_file
    globals()["LOCAL_TEXT_EXPORT_FILE"] = paths.text_export_file
    globals()["SYNC_STATE_FILE"] = paths.sync_state_file


def create_web_app(
    *,
    config=Config,
    base_dir: Path | None = None,
    paths: AppPaths | None = None,
) -> KassensturzWebApp:
    return KassensturzWebApp(config=config, base_dir=base_dir, paths=paths)


def create_app(
    *,
    config=Config,
    base_dir: Path | None = None,
    paths: AppPaths | None = None,
) -> Flask:
    return create_web_app(config=config, base_dir=base_dir, paths=paths).flask_app


web_app = create_web_app()
app = web_app.flask_app
_sync_legacy_path_globals(web_app.paths)


if __name__ == "__main__":
    debug = web_app.config.MODE == "debug" and not getattr(
        web_app.config,
        "IS_FROZEN",
        False,
    )
    app.run(debug=debug, use_reloader=debug)
