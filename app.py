from functools import wraps
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, session, url_for
import mimetypes
import logging

from core.logging_config import setup_logging
from config import Config
from core import storage
from core import sync_state
from core.cash_service import (
    rebuild_exports_and_sync,
    record_cash_count_and_sync,
    record_cash_movement_and_sync,
)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY


mimetypes.add_type("application/javascript", ".js")

logger = logging.getLogger(__name__)


# ============================================================================
# Local paths
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / Config.MODE
BACKUP_DIR = DATA_DIR / "backups"

LOCAL_DB_FILE = DATA_DIR / "kassensturz.db"
LOCAL_EXCEL_EXPORT_FILE = DATA_DIR / "kassensturz_data.xlsx"
LOCAL_TEXT_EXPORT_FILE = DATA_DIR / "kassensturz_data.txt"
SYNC_STATE_FILE = DATA_DIR / "sync_state.json"

setup_logging(BASE_DIR, debug=(Config.MODE == "debug"))
logger = logging.getLogger(__name__)
logger.info("App startup | mode=%s db=%s", Config.MODE, LOCAL_DB_FILE)


# ============================================================================
# Startup
# ============================================================================

storage.ensure_db_file(LOCAL_DB_FILE)
storage.seed_default_cash_accounts(LOCAL_DB_FILE)


# ============================================================================
# Helpers
# ============================================================================

def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapped


def _parse_cents_from_form_amount(raw_value: str) -> int:
    raw_value = str(raw_value).strip().replace(",", ".")
    return storage.eur_to_cents(raw_value)


def _common_template_context():
    return {
        "cash_accounts": storage.fetch_all_cash_accounts(LOCAL_DB_FILE, active_only=True),
        "recent_contexts": storage.fetch_recent_cash_contexts(LOCAL_DB_FILE, limit=20),
        "latest_context_label": storage.get_latest_cash_context_label(LOCAL_DB_FILE),
        "count_types": [
            storage.COUNT_TYPE_OPENING,
            storage.COUNT_TYPE_CLOSING,
            storage.COUNT_TYPE_SPOT_CHECK,
            storage.COUNT_TYPE_HANDOVER,
            storage.COUNT_TYPE_RECONCILIATION,
        ],
        "denom_fields": storage.DENOM_FIELDS,
        "mode": Config.MODE,
    }


def _get_denominations_from_request_form():
    return storage.get_denomination_values_from_form(request.form)



# ============================================================================
# Main count route
# ============================================================================

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            cash_account_id = request.form.get("cash_account_id", "").strip()
            counted_by = request.form.get("counted_by", "").strip()
            count_type = request.form.get("count_type", "").strip()
            context_label = request.form.get("context_label", "").strip()
            note = request.form.get("note", "").strip()

            denominations = _get_denominations_from_request_form()

            raw_total = request.form.get("total_eur", "").strip()
            if raw_total:
                total_cents = _parse_cents_from_form_amount(raw_total)
            else:
                total_cents = storage.calculate_total_cents_from_denominations(
                    denominations
                )

            logger.info(
                "Count form submitted | account=%s counted_by=%s type=%s context=%s",
                cash_account_id,
                counted_by,
                count_type,
                context_label,
            )

            result = record_cash_count_and_sync(
                db_path=LOCAL_DB_FILE,
                excel_path=LOCAL_EXCEL_EXPORT_FILE,
                text_path=LOCAL_TEXT_EXPORT_FILE,
                backup_dir=BACKUP_DIR,
                sync_state_file=SYNC_STATE_FILE,
                config=Config,
                cash_account_id=cash_account_id,
                counted_by=counted_by,
                total_cents=total_cents,
                count_type=count_type,
                context_label=context_label,
                note=note,
                denominations=denominations,
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
            logger.exception("Failed to record cash count")
            flash(f"Failed to record cash count: {exc}", "error")

    context = _common_template_context()
    context["recent_counts"] = storage.fetch_recent_cash_counts(LOCAL_DB_FILE, limit=20)
    return render_template("index.html", **context)


# ============================================================================
# Cash movement route
# ============================================================================

@app.route("/cash/movement", methods=["GET", "POST"])
def cash_movement():
    if request.method == "POST":
        try:
            from_account_id = request.form.get("from_account_id", "").strip() or None
            to_account_id = request.form.get("to_account_id", "").strip() or None
            actor = request.form.get("actor", "").strip()
            reference = request.form.get("reference", "").strip()
            note = request.form.get("note", "").strip()
            context_label = request.form.get("context_label", "").strip()
            amount_cents = _parse_cents_from_form_amount(
                request.form.get("amount_eur", "").strip()
            )

            logger.info(
                "Movement form submitted | type=%s from=%s to=%s actor=%s context=%s",
                from_account_id,
                to_account_id,
                actor,
                context_label,
            )
            denominations = _get_denominations_from_request_form()

            result = record_cash_movement_and_sync(
                db_path=LOCAL_DB_FILE,
                excel_path=LOCAL_EXCEL_EXPORT_FILE,
                text_path=LOCAL_TEXT_EXPORT_FILE,
                backup_dir=BACKUP_DIR,
                sync_state_file=SYNC_STATE_FILE,
                config=Config,
                amount_cents=amount_cents,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                context_label=context_label,
                actor=actor,
                reference=reference,
                note=note,
                denominations=denominations,
            )

            flash(
                (
                    f"Cash movement recorded. "
                    f"Imported counts: {result['imported_counts']}, "
                    f"imported movements: {result['imported_movements']}."
                ),
                "movement_success",
            )
            return redirect(url_for("cash_movement"))

        except Exception as exc:
            logger.exception("Failed to record cash movement")
            flash(f"Failed to record cash movement: {exc}", "error")

    context = _common_template_context()
    context["recent_movements"] = storage.fetch_recent_cash_movements(
        LOCAL_DB_FILE,
        limit=20,
    )
    return render_template("cash_movement.html", **context)

# ============================================================================
# Cash Balance route
# ============================================================================

@app.route("/balances")
def balances():
    context = {
        **_common_template_context(),
        "balances": storage.fetch_cash_account_balances(LOCAL_DB_FILE),
        "recent_counts": storage.fetch_recent_cash_counts(LOCAL_DB_FILE, limit=4),
        "recent_movements": storage.fetch_recent_cash_movements(LOCAL_DB_FILE, limit=4),
    }
    return render_template("balances.html", **context)

# ============================================================================
# Admin auth
# ============================================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        submitted_password = request.form.get("password", "")
        if submitted_password == Config.ADMIN_PASSWORD:
            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        flash("Invalid password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out.", "admin_success")
    return redirect(url_for("index"))




# ============================================================================
# Admin dashboard
# ============================================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    context = {
        **_common_template_context(),
        "available_backups": storage.list_backups(BACKUP_DIR),
        "sync_state_data": sync_state.load_sync_state(SYNC_STATE_FILE),
        "row_counts": {
            "cash_accounts": storage.get_row_count(LOCAL_DB_FILE, "cash_accounts"),
            "cash_contexts": storage.get_row_count(LOCAL_DB_FILE, "cash_contexts"),
            "cash_movements": storage.get_row_count(LOCAL_DB_FILE, "cash_movements"),
            "cash_counts": storage.get_row_count(LOCAL_DB_FILE, "cash_counts"),
        },
    }
    return render_template("admin.html", **context)

@app.route("/admin/restore-backup", methods=["POST"])
@admin_required
def admin_restore_backup():
    try:
        backup_name = request.form.get("backup_name", "").strip()
        if not backup_name:
            raise ValueError("No backup selected.")

        backup_file = BACKUP_DIR / backup_name

        storage.restore_backup(
            db_path=LOCAL_DB_FILE,
            backup_file=backup_file,
        )

        # optional but useful: rebuild exports after restore
        rebuild_exports_and_sync(
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
            backup_dir=BACKUP_DIR,
            sync_state_file=SYNC_STATE_FILE,
            config=Config,
        )

        flash(f"Backup restored: {backup_name}", "admin_success")

    except Exception as exc:
        logger.exception("Backup restore failed")
        flash(f"Restore failed: {exc}", "error")

    return redirect(url_for("admin_dashboard"))

# ============================================================================
# Admin actions
# ============================================================================

@app.route("/admin/rebuild-exports", methods=["POST"])
@admin_required
def admin_rebuild_exports():
    try:
        result = rebuild_exports_and_sync(
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
            backup_dir=BACKUP_DIR,
            sync_state_file=SYNC_STATE_FILE,
            config=Config,
        )
        flash(
            (
                f"Rebuild + sync complete. "
                f"Imported counts: {result['imported_counts']}, "
                f"imported movements: {result['imported_movements']}."
            ),
            "admin_success",
        )
    except Exception as exc:
        logger.exception("Manual rebuild failed")
        flash(f"Rebuild failed: {exc}", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/sync-now", methods=["POST"])
@admin_required
def admin_sync_now():
    try:
        result = rebuild_exports_and_sync(
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
            backup_dir=BACKUP_DIR,
            sync_state_file=SYNC_STATE_FILE,
            config=Config,
        )
        flash(
            (
                f"Sync complete. "
                f"Imported counts: {result['imported_counts']}, "
                f"imported movements: {result['imported_movements']}."
            ),
            "admin_success",
        )
    except Exception as exc:
        logger.exception("Manual sync failed")
        flash(f"Sync failed: {exc}", "error")

    return redirect(url_for("admin_dashboard"))


# ============================================================================
# App entry
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True)