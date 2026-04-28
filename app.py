import mimetypes
import os
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from config import Config

from core.storage import (
    create_backup,
    ensure_db_file,
    get_denomination_values_from_form,
    insert_entry,
    merge_imported_entries_append_only,
    new_entry_id,
)

from core.export_utils import (
    export_entries_to_excel,
    export_entries_to_text,
    import_entries_from_excel,
)

from core.nextcloud_sync import (
    download_remote_excel_to_temp,
    nextcloud_configured,
    upload_excel_file_to_nextcloud,
    upload_text_file_to_nextcloud,
)
from core.service import append_and_sync

mimetypes.add_type("application/javascript", ".js")

print(f"[Kassensturz] MODE = {Config.MODE}")
print(f"[Kassensturz] FROZEN = {getattr(sys, 'frozen', False)}")


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


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    ensure_db_file(LOCAL_DB_FILE)
    threading.Timer(1.0, open_browser).start()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=is_debug_mode(),
        use_reloader=False,
    )