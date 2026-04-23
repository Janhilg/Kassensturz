class Config:
    # Nextcloud settings (fallback defaults)
    NEXTCLOUD_BASE_URL = "https://nx94183.your-storageshare.de/"
    NEXTCLOUD_USERNAME = "jan.hilgenfeld@hotmail.com"
    NEXTCLOUD_APP_PASSWORD = ";926nkxEHy#?XG!a"

    NEXTCLOUD_REMOTE_DIR = "Kassensturz"
    NEXTCLOUD_REMOTE_FILE = "kassensturz_data.xlsx"

    # Path to a CA bundle or CA cert that signs your Nextcloud certificate
    NEXTCLOUD_CA_CERT_PATH = ""
    NEXTCLOUD_VERIFY = "false"