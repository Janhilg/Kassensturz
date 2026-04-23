import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from openpyxl import Workbook, load_workbook

from config import Config

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

EXCEL_FILE = Path("data/kassensturz_data.xlsx")

NEXTCLOUD_BASE_URL = Config.NEXTCLOUD_BASE_URL.rstrip("/")
NEXTCLOUD_USERNAME = Config.NEXTCLOUD_USERNAME
NEXTCLOUD_APP_PASSWORD = Config.NEXTCLOUD_APP_PASSWORD
NEXTCLOUD_REMOTE_DIR = Config.NEXTCLOUD_REMOTE_DIR
NEXTCLOUD_REMOTE_FILE = Config.NEXTCLOUD_REMOTE_FILE

PRETIX_BASE_URL = Config.PRETIX_BASE_URL.rstrip("/")
PRETIX_ORGANIZER = Config.PRETIX_ORGANIZER
PRETIX_API_TOKEN = Config.PRETIX_API_TOKEN
PRETIX_EVENT_SLUG = Config.PRETIX_EVENT_SLUG


def get_verify_setting():
    if Config.NEXTCLOUD_VERIFY.lower() == "false":
        return False
    if Config.NEXTCLOUD_CA_CERT_PATH:
        return Config.NEXTCLOUD_CA_CERT_PATH
    return True


def ensure_excel_file():
    EXCEL_FILE.parent.mkdir(parents=True, exist_ok=True)

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
        verify=get_verify_setting(),
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
            verify=get_verify_setting(),
        )

    if response.status_code not in (200, 201, 204):
        raise RuntimeError(
            f"Failed to upload Excel file to Nextcloud: "
            f"{response.status_code} {response.text}"
        )


def pretix_configured():
    return all([
        PRETIX_BASE_URL,
        PRETIX_ORGANIZER,
        PRETIX_API_TOKEN,
    ])


def pretix_headers():
    return {
        "Authorization": f"Token {PRETIX_API_TOKEN}",
        "Accept": "application/json",
    }


def parse_pretix_datetime(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_pretix_event_name(event):
    name = event.get("name")
    if isinstance(name, dict):
        return name.get("en") or next(iter(name.values()), "")
    return name or ""


def get_specific_pretix_event():
    if not pretix_configured() or not PRETIX_EVENT_SLUG:
        return None

    url = (
        f"{PRETIX_BASE_URL}/api/v1/organizers/"
        f"{PRETIX_ORGANIZER}/events/{PRETIX_EVENT_SLUG}/"
    )
    response = requests.get(url, headers=pretix_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def get_pretix_events():
    if not pretix_configured():
        return []

    url = f"{PRETIX_BASE_URL}/api/v1/organizers/{PRETIX_ORGANIZER}/events/"
    params = {
        "is_future": "true",
    }
    response = requests.get(url, headers=pretix_headers(), params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("results", [])


def get_current_pretix_event():
    if PRETIX_EVENT_SLUG:
        event = get_specific_pretix_event()
        return {
            "slug": event.get("slug"),
            "name": get_pretix_event_name(event),
            "date_from": event.get("date_from"),
            "date_to": event.get("date_to"),
            "public_url": event.get("public_url"),
            "timezone": event.get("timezone"),
            "live": event.get("live"),
        }

    now = datetime.now(timezone.utc)
    events = get_pretix_events()

    running_events = []
    upcoming_events = []

    for event in events:
        date_from = parse_pretix_datetime(event.get("date_from"))
        date_to = parse_pretix_datetime(event.get("date_to"))

        if date_from and date_to:
            if date_from <= now <= date_to:
                running_events.append(event)
            elif now < date_from:
                upcoming_events.append(event)
        elif date_from:
            if date_from <= now:
                running_events.append(event)
            else:
                upcoming_events.append(event)

    if running_events:
        running_events.sort(key=lambda e: parse_pretix_datetime(e.get("date_from")) or datetime.max.replace(tzinfo=timezone.utc))
        chosen = running_events[0]
    elif upcoming_events:
        upcoming_events.sort(key=lambda e: parse_pretix_datetime(e.get("date_from")) or datetime.max.replace(tzinfo=timezone.utc))
        chosen = upcoming_events[0]
    else:
        return None

    return {
        "slug": chosen.get("slug"),
        "name": get_pretix_event_name(chosen),
        "date_from": chosen.get("date_from"),
        "date_to": chosen.get("date_to"),
        "public_url": chosen.get("public_url"),
        "timezone": chosen.get("timezone"),
        "live": chosen.get("live"),
    }


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


@app.route("/api/current-event", methods=["GET"])
def current_event():
    try:
        event = get_current_pretix_event()
        return jsonify({
            "ok": True,
            "event": event,
        })
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 500


if __name__ == "__main__":
    ensure_excel_file()
    app.run(host="0.0.0.0", port=5000, debug=True)