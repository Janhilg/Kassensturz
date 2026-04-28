import mimetypes
import os
import sys
import threading
import webbrowser
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, url_for, session

from config import Config
from core.service import append_and_sync
from core.logging_config import setup_logging
from core.admin_service import (
    get_status_snapshot,
    rebuild_exports,
    restore_backup,
    sync_exports_now,
)
from core.storage import (
    ensure_db_file,
    get_denomination_values_from_form,
    new_entry_id,
)

mimetypes.add_type("application/javascript", ".js")

logger = logging.getLogger(__name__)
logger.info(f"MODE = {Config.MODE}")
logger.info(f"FROZEN = {getattr(sys, 'frozen', False)}")


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def portable_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_debug_mode() -> bool:
    return Config.MODE == "debug" and not Config.IS_FROZEN


def get_form_value(name: str) -> str:
    return request.form.get(name, "").strip()

def require_admin_password_or_reject():
    expected = getattr(Config, "ADMIN_PASSWORD", "").strip()

    if not expected:
        raise PermissionError("ADMIN_PASSWORD is not configured.")

    submitted = request.form.get("admin_password", "").strip()

    if submitted != expected:
        raise PermissionError("Invalid admin password.")

def is_admin_authenticated() -> bool:
    return session.get("admin_authenticated") is True


def require_admin_login():
    if not is_admin_authenticated():
        return redirect(url_for("admin_login"))

BASE_DIR = portable_base_dir()
DATA_DIR = BASE_DIR / ("data_debug" if is_debug_mode() else "data")

LOCAL_DB_FILE = DATA_DIR / "kassensturz.db"
BACKUP_DIR = DATA_DIR / "backups"
LOCAL_EXCEL_EXPORT_FILE = DATA_DIR / "kassensturz_data.xlsx"
LOCAL_TEXT_EXPORT_FILE = DATA_DIR / "kassensturz_data.txt"

template_dir = resource_path("templates")
static_dir = resource_path("static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        submitted_text = get_form_value("text_input")
        submitted_counted_by = get_form_value("counted_by_input")
        submitted_number = get_form_value("number_input")
        submitted_event_state = get_form_value("event_state")
        submitted_comment = get_form_value("comment_input")

        try:
            denominations = get_denomination_values_from_form(request.form)
        except Exception:
            flash("Invalid denomination input.", "error")
            return redirect(url_for("home"))

        if submitted_text and submitted_counted_by and submitted_number and submitted_event_state:
            try:
                now = datetime.now()
                current_date = now.strftime("%Y-%m-%d")
                current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

                entry = {
                    "id": new_entry_id(),
                    "date": current_date,
                    "timestamp": current_timestamp,
                    "event_name": submitted_text,
                    "counted_by": submitted_counted_by,
                    "cash_sum": float(submitted_number),
                    "event_status": submitted_event_state,
                    "comment": submitted_comment,
                    **denominations,
                }

                append_and_sync(
                    entry=entry,
                    db_path=LOCAL_DB_FILE,
                    backup_dir=BACKUP_DIR,
                    excel_path=LOCAL_EXCEL_EXPORT_FILE,
                    text_path=LOCAL_TEXT_EXPORT_FILE,
                    config=Config,
                    base_dir=BASE_DIR,
                    is_debug=is_debug_mode(),
                )

                flash(
                    {
                        "date": current_date,
                        "timestamp": current_timestamp,
                        "text": submitted_text,
                        "counted_by": submitted_counted_by,
                        "number": submitted_number,
                        "event_state": submitted_event_state,
                        "comment": submitted_comment,
                        "denominations": denominations,
                    },
                    "submitted",
                )

                return redirect(url_for("home"))

            except Exception as exc:
                flash(str(exc), "error")
                return redirect(url_for("home"))

    return render_template("index.html", app_mode=Config.MODE)

@app.route("/admin", methods=["GET"])
def admin():
    if not is_admin_authenticated():
        return redirect(url_for("admin_login"))

    status = get_status_snapshot(
        db_path=LOCAL_DB_FILE,
        backup_dir=BACKUP_DIR,
        excel_path=LOCAL_EXCEL_EXPORT_FILE,
        text_path=LOCAL_TEXT_EXPORT_FILE,
        config=Config,
    )

    return render_template(
        "admin.html",
        app_mode=Config.MODE,
        status=status,
        admin_logged_in=is_admin_authenticated(),
    )

@app.route("/admin/restore-backup", methods=["POST"])
def admin_restore_backup():
    if not is_admin_authenticated():
        return redirect(url_for("admin_login"))

    backup_name = request.form.get("backup_name", "").strip()
    if not backup_name:
        flash("No backup selected.", "error")
        return redirect(url_for("admin"))

    backup_file = BACKUP_DIR / backup_name

    try:
        restore_backup(
            backup_file=backup_file,
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
            config=Config,
            base_dir=BASE_DIR,
        )

        logger.info("Backup restored | backup=%s", backup_name)
        flash(f"Backup restored: {backup_name}", "success")

    except Exception as exc:
        logger.exception("Backup restore failed | backup=%s", backup_name)
        flash(str(exc), "error")

    return redirect(url_for("admin"))

@app.route("/admin/rebuild-exports", methods=["POST"])
def admin_rebuild_exports():
    if not is_admin_authenticated():
        return redirect(url_for("admin_login"))

    try:
        rebuild_exports(
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
        )

        logger.info("Admin rebuild exports completed")
        flash("Exports rebuilt successfully.", "success")

    except Exception as exc:
        logger.exception("Admin rebuild exports failed")
        flash(str(exc), "error")

    return redirect(url_for("admin"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if password == Config.ADMIN_PASSWORD:
            session["admin_authenticated"] = True
            return redirect(url_for("admin"))
        else:
            flash("Invalid admin password.", "error")

    return render_template("admin_login.html", app_mode=Config.MODE)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    return redirect(url_for("home"))

@app.route("/admin/sync-now", methods=["POST"])
def admin_sync_now():
    if not is_admin_authenticated():
        return redirect(url_for("admin_login"))

    try:
        sync_exports_now(
            db_path=LOCAL_DB_FILE,
            excel_path=LOCAL_EXCEL_EXPORT_FILE,
            text_path=LOCAL_TEXT_EXPORT_FILE,
            config=Config,
            base_dir=BASE_DIR,
        )

        logger.info("Admin sync now completed")
        flash("Sync completed successfully.", "success")

    except Exception as exc:
        logger.exception("Admin sync now failed")
        flash(str(exc), "error")

    return redirect(url_for("admin"))

@app.context_processor
def inject_admin_state():
    return {
        "admin_logged_in": is_admin_authenticated(),
    }

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    setup_logging(BASE_DIR, is_debug_mode())
    ensure_db_file(LOCAL_DB_FILE)
    threading.Timer(1.0, open_browser).start()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=is_debug_mode(),
        use_reloader=False,
    )