import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, flash, redirect, render_template, request, url_for
from openpyxl import Workbook, load_workbook

from config import Config

import mimetypes
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

def is_debug_mode():
    return Config.MODE == "debug" and not Config.IS_FROZEN

template_dir = resource_path("templates")
static_dir = resource_path("static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

EXCEL_HEADERS = [
    "Date",
    "Timestamp",
    "Event name",
    "Counted by",
    "Cash sum",
    "Event status",
    "Comment",
]

BASE_DIR = portable_base_dir()

if  is_debug_mode():
    LOCAL_EXCEL_FILE = BASE_DIR / "data_debug" / "kassensturz_data.xlsx"
    BACKUP_DIR = BASE_DIR / "data_debug" / "backups"
else:
    LOCAL_EXCEL_FILE = BASE_DIR / "data" / "kassensturz_data.xlsx"
    BACKUP_DIR = BASE_DIR / "data" / "backups"

NEXTCLOUD_BASE_URL = Config.NEXTCLOUD_BASE_URL.rstrip("/")
NEXTCLOUD_USERNAME = Config.NEXTCLOUD_USERNAME
NEXTCLOUD_APP_PASSWORD = Config.NEXTCLOUD_APP_PASSWORD
NEXTCLOUD_REMOTE_DIR = Config.NEXTCLOUD_REMOTE_DIR
NEXTCLOUD_REMOTE_FILE = Config.NEXTCLOUD_REMOTE_FILE


def get_verify_setting():
    if getattr(Config, "NEXTCLOUD_VERIFY", "true").lower() == "false":
        return False

    ca_cert_path = getattr(Config, "NEXTCLOUD_CA_CERT_PATH", "")
    if ca_cert_path:
        ca_path = Path(ca_cert_path)
        if not ca_path.is_absolute():
            ca_path = BASE_DIR / ca_path
        return str(ca_path)

    return True


def nextcloud_configured():
    return all([
        NEXTCLOUD_BASE_URL,
        NEXTCLOUD_USERNAME,
        NEXTCLOUD_APP_PASSWORD,
    ])


def build_webdav_url(path: str) -> str:
    encoded_path = "/".join(quote(part) for part in path.strip("/").split("/"))
    return (
        f"{NEXTCLOUD_BASE_URL}/remote.php/dav/files/"
        f"{quote(NEXTCLOUD_USERNAME)}/{encoded_path}"
    )


def ensure_local_excel_file():
    LOCAL_EXCEL_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not LOCAL_EXCEL_FILE.exists():
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Kassensturz"
        sheet.append(EXCEL_HEADERS)
        workbook.save(LOCAL_EXCEL_FILE)


def create_empty_excel_file(file_path: Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Kassensturz"
    sheet.append(EXCEL_HEADERS)
    workbook.save(file_path)


def ensure_nextcloud_folder():
    if not nextcloud_configured():
        return

    parts = [part for part in NEXTCLOUD_REMOTE_DIR.strip("/").split("/") if part]
    current_path = ""

    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part
        url = build_webdav_url(current_path)

        response = requests.request(
            "MKCOL",
            url,
            auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_APP_PASSWORD),
            timeout=30,
            verify=get_verify_setting(),
        )

        # 201 = created, 405 = already exists
        if response.status_code not in (201, 405):
            raise RuntimeError(
                f"Failed to create Nextcloud folder '{current_path}': "
                f"{response.status_code} {response.text}"
            )

def normalize_row_length(row, target_length):
    row = list(row)
    if len(row) < target_length:
        row.extend([""] * (target_length - len(row)))
    return tuple(row[:target_length])


# Migration for older Excel file columns.
def upgrade_file_format(file_path: Path):
    workbook = load_workbook(file_path)
    sheet = workbook.active

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        sheet.append(EXCEL_HEADERS)
        workbook.save(file_path)
        return

    header = [str(cell) if cell is not None else "" for cell in rows[0]]

    if header == EXCEL_HEADERS:
        return

    existing_data = rows[1:] if rows else []

    # Previous format: Date, Timestamp, Event name, Cash sum, Event status, Comment
    if header[:6] == ["Date", "Timestamp", "Event name", "Cash sum", "Event status", "Comment"]:
        sheet.delete_rows(1, sheet.max_row)
        sheet.append(EXCEL_HEADERS)

        for row in existing_data:
            row = list(row)
            date_value = row[0] if len(row) > 0 else ""
            timestamp_value = row[1] if len(row) > 1 else ""
            event_name = row[2] if len(row) > 2 else ""
            cash_sum = row[3] if len(row) > 3 else ""
            event_state = row[4] if len(row) > 4 else ""
            comment = row[5] if len(row) > 5 else ""
            sheet.append([
                date_value,
                timestamp_value,
                event_name,
                "",
                cash_sum,
                event_state,
                comment,
            ])

        workbook.save(file_path)
        return

    raise RuntimeError(
        "Unsupported Excel format. Expected current format or previous format without 'Counted by'."
    )


def append_to_excel_file(
    file_path: Path,
    date_value: str,
    timestamp_value: str,
    event_name: str,
    counted_by: str,
    cash_sum: float,
    event_state: str,
    comment: str,
):
    upgrade_file_format(file_path)

    workbook = load_workbook(file_path)
    sheet = workbook.active
    sheet.append([
        date_value,
        timestamp_value,
        event_name,
        counted_by,
        cash_sum,
        event_state,
        comment,
    ])
    workbook.save(file_path)


def read_rows(file_path: Path):
    upgrade_file_format(file_path)

    workbook = load_workbook(file_path, data_only=True)
    sheet = workbook.active
    rows = [tuple(row) for row in sheet.iter_rows(values_only=True)]

    if not rows:
        return []

    data_rows = rows[1:]
    return [normalize_row_length(row, len(EXCEL_HEADERS)) for row in data_rows]


def parse_timestamp_for_sort(row):
    timestamp_value = row[1] if len(row) > 1 else ""
    if timestamp_value:
        try:
            return datetime.strptime(str(timestamp_value), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    date_value = row[0] if len(row) > 0 else ""
    if date_value:
        try:
            return datetime.strptime(str(date_value), "%Y-%m-%d")
        except ValueError:
            pass

    return datetime.min


def rewrite_excel_file(file_path: Path, data_rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Kassensturz"
    sheet.append(EXCEL_HEADERS)

    for row in data_rows:
        normalized = normalize_row_length(row, len(EXCEL_HEADERS))
        sheet.append(list(normalized))

    workbook.save(file_path)


def merge_remote_into_local(remote_file: Path, local_file: Path):
    remote_rows = read_rows(remote_file)
    local_rows = read_rows(local_file)

    combined = []
    seen = set()

    for row in local_rows + remote_rows:
        normalized = normalize_row_length(row, len(EXCEL_HEADERS))
        if normalized not in seen:
            seen.add(normalized)
            combined.append(normalized)

    combined.sort(key=parse_timestamp_for_sort)
    rewrite_excel_file(local_file, combined)


def download_remote_to_temp(temp_path: Path):
    if not nextcloud_configured():
        return False

    remote_path = f"{NEXTCLOUD_REMOTE_DIR}/{NEXTCLOUD_REMOTE_FILE}"
    url = build_webdav_url(remote_path)

    response = requests.get(
        url,
        auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_APP_PASSWORD),
        timeout=60,
        verify=get_verify_setting(),
    )

    if response.status_code == 200:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("wb") as f:
            f.write(response.content)
        return True

    if response.status_code == 404:
        return False

    raise RuntimeError(
        f"Failed to download Excel file from Nextcloud: "
        f"{response.status_code} {response.text}"
    )


def create_backup(max_backups: int = 25):
    ensure_local_excel_file()
    upgrade_file_format(LOCAL_EXCEL_FILE)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"kassensturz_backup_{timestamp}.xlsx"
    shutil.copy2(LOCAL_EXCEL_FILE, backup_file)

    backups = sorted(
        BACKUP_DIR.glob("kassensturz_backup_*.xlsx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for old_file in backups[max_backups:]:
        try:
            old_file.unlink()
        except Exception:
            pass

    return backup_file


def upload_excel_file_to_nextcloud(file_path: Path):
    if not nextcloud_configured():
        return

    ensure_nextcloud_folder()

    remote_path = f"{NEXTCLOUD_REMOTE_DIR}/{NEXTCLOUD_REMOTE_FILE}"
    url = build_webdav_url(remote_path)

    print(f"[Kassensturz] Uploading to: {remote_path}")
    print(f"[Kassensturz] WebDAV URL: {url}")

    with file_path.open("rb") as file_handle:
        response = requests.put(
            url,
            data=file_handle,
            auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_APP_PASSWORD),
            headers={
                "Content-Type": (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            },
            timeout=60,
            verify=get_verify_setting(),
        )

    print(f"[Kassensturz] Upload response: {response.status_code}")
    print(f"[Kassensturz] Upload response body: {response.text[:500]}")

    if response.status_code not in (200, 201, 204):
        raise RuntimeError(
            f"Failed to upload Excel file to Nextcloud: "
            f"{response.status_code} {response.text}"
        )


def append_and_sync(date_value, timestamp_value, event_name, counted_by, cash_sum, event_state, comment):
    ensure_local_excel_file()

    append_to_excel_file(
        LOCAL_EXCEL_FILE,
        date_value,
        timestamp_value,
        event_name,
        counted_by,
        cash_sum,
        event_state,
        comment,
    )

    if nextcloud_configured():
        flash("upload_success" f"{NEXTCLOUD_REMOTE_DIR}/{NEXTCLOUD_REMOTE_FILE}", "success")

    if not nextcloud_configured():
        return

    # Debug mode:
    # keep local file and upload directly to the debug Nextcloud path
    # without merging remote content back in.
    if is_debug_mode():
        create_backup()
        upload_excel_file_to_nextcloud(LOCAL_EXCEL_FILE)
        return

    # Production mode:
    # merge local + remote, then upload
    with tempfile.TemporaryDirectory() as tmp_dir:
        remote_file = Path(tmp_dir) / "remote.xlsx"
        remote_exists = download_remote_to_temp(remote_file)

        if remote_exists:
            merge_remote_into_local(remote_file, LOCAL_EXCEL_FILE)

    create_backup()
    upload_excel_file_to_nextcloud(LOCAL_EXCEL_FILE)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        submitted_text = request.form.get("text_input", "").strip()
        submitted_counted_by = request.form.get("counted_by_input", "").strip()
        submitted_number = request.form.get("number_input", "").strip()
        submitted_event_state = request.form.get("event_state", "").strip()
        submitted_comment = request.form.get("comment_input", "").strip()

        if submitted_text and submitted_counted_by and submitted_number and submitted_event_state:
            try:
                now = datetime.now()
                current_date = now.strftime("%Y-%m-%d")
                current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

                append_and_sync(
                    current_date,
                    current_timestamp,
                    submitted_text,
                    submitted_counted_by,
                    float(submitted_number),
                    submitted_event_state,
                    submitted_comment,
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
    ensure_local_excel_file()
    upgrade_file_format(LOCAL_EXCEL_FILE)

    threading.Timer(1.0, open_browser).start()

    app.run(host="127.0.0.1", port=5000, debug= is_debug_mode())