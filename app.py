import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from openpyxl import Workbook, load_workbook

from config import Config

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"

EXCEL_FILE = Path("kassensturz_data.xlsx")

NEXTCLOUD_BASE_URL = Config.NEXTCLOUD_BASE_URL.rstrip("/")
NEXTCLOUD_USERNAME = Config.NEXTCLOUD_USERNAME
NEXTCLOUD_APP_PASSWORD = Config.NEXTCLOUD_APP_PASSWORD
NEXTCLOUD_REMOTE_DIR = Config.NEXTCLOUD_REMOTE_DIR
NEXTCLOUD_REMOTE_FILE = Config.NEXTCLOUD_REMOTE_FILE


def ensure_excel_file():
    if not EXCEL_FILE.exists():
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Kassensturz"
        sheet.append(["Date", "Event name", "Cash sum", "Comment"])
        workbook.save(EXCEL_FILE)


def append_to_excel(date_value, event_name, cash_sum, comment):
    ensure_excel_file()
    workbook = load_workbook(EXCEL_FILE)
    sheet = workbook.active
    sheet.append([date_value, event_name, cash_sum, comment])
    workbook.save(EXCEL_FILE)


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


def ensure_nextcloud_folder():
    if not nextcloud_configured():
        return

    url = build_webdav_url(NEXTCLOUD_REMOTE_DIR)
    response = requests.request(
        "MKCOL",
        url,
        auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_APP_PASSWORD),
        timeout=30,
        verify=False  # replace with your proper cert config if needed
    )

    if response.status_code not in (201, 405):
        raise RuntimeError(
            f"Failed to create Nextcloud folder: "
            f"{response.status_code} {response.text}"
        )


def upload_excel_to_nextcloud():
    if not nextcloud_configured():
        return

    ensure_nextcloud_folder()

    remote_path = f"{NEXTCLOUD_REMOTE_DIR}/{NEXTCLOUD_REMOTE_FILE}"
    url = build_webdav_url(remote_path)

    with EXCEL_FILE.open("rb") as file_handle:
        response = requests.put(
            url,
            data=file_handle,
            auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_APP_PASSWORD),
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            timeout=60,
            verify=False  # replace with your proper cert config if needed
        )

    if response.status_code not in (200, 201, 204):
        raise RuntimeError(
            f"Failed to upload Excel file to Nextcloud: "
            f"{response.status_code} {response.text}"
        )


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        submitted_text = request.form.get("text_input", "").strip()
        submitted_number = request.form.get("number_input", "").strip()
        submitted_comment = request.form.get("comment_input", "").strip()

        if submitted_text and submitted_number:
            try:
                current_date = datetime.now().strftime("%Y-%m-%d")
                append_to_excel(
                    current_date,
                    submitted_text,
                    float(submitted_number),
                    submitted_comment,
                )
                upload_excel_to_nextcloud()

                flash({
                    "text": submitted_text,
                    "number": submitted_number,
                    "comment": submitted_comment,
                    "date": current_date,
                }, "submitted")

                return redirect(url_for("home"))

            except Exception as exc:
                flash(str(exc), "error")
                return redirect(url_for("home"))

    return render_template("index.html")


if __name__ == "__main__":
    ensure_excel_file()
    app.run(host="0.0.0.0", port=5000, debug=True)