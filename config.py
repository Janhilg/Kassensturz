import os

class Config:
    # Nextcloud settings (fallback defaults)
    NEXTCLOUD_BASE_URL = ""
    NEXTCLOUD_USERNAME = ""
    NEXTCLOUD_APP_PASSWORD = ""

    NEXTCLOUD_REMOTE_DIR = "Kassensturz"
    NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"

    # Path to a CA bundle or CA cert that signs your Nextcloud certificate
    NEXTCLOUD_CA_CERT_PATH = ""
    NEXTCLOUD_VERIFY = "false"