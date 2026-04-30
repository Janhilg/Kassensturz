import sys

class Config:
    # =========================
    # Detect PyInstaller build
    # =========================
    IS_FROZEN = getattr(sys, "frozen", False)

    # =========================
    # App Mode / Mode-based path
    # =========================
    PRODUCTION_MODE = "false"
    if PRODUCTION_MODE == "true":
        NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz"
        NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
        MODE = "production"
    else:
        NEXTCLOUD_REMOTE_DIR = "Apps/Kassensturz/Debug"
        NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"
        MODE = "debug"

    # =========================
    # App Mode PyInstaller build
    # =========================
    if IS_FROZEN:
        MODE = "production"

    # =========================
    # Nextcloud credentials
    # =========================
    NEXTCLOUD_BASE_URL = ""
    NEXTCLOUD_USERNAME = ""
    NEXTCLOUD_APP_PASSWORD = ""

    # =========================
    # SSL handling
    # =========================
    # unused - does require to get a valid cert
    NEXTCLOUD_CA_CERT_PATH = ""
    NEXTCLOUD_VERIFY = "false"

    # =========================
    # Flask Key
    # =========================
    SECRET_KEY = ""

    # =========================
    # Admin page password
    # =========================
    ADMIN_PASSWORD = ""
