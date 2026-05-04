from base64 import b64decode


def _d(*chunks: str) -> str:
    return b64decode("".join(chunks)).decode("utf-8")


BUNDLED_CONFIG = {
    "KASSENSTURZ_MODE": _d("debug"),
    "KASSENSTURZ_SECRET_KEY": _d("change_this"),
    "KASSENSTURZ_ADMIN_PASSWORD": _d("Your_admin_password"),
    "KASSENSTURZ_NEXTCLOUD_BASE_URL": _d("https://123.example.com/"),
    "KASSENSTURZ_NEXTCLOUD_USERNAME": _d("user@example.com"),
    "KASSENSTURZ_NEXTCLOUD_APP_PASSWORD": _d("your_nextcloud_user_password"),
    "KASSENSTURZ_NEXTCLOUD_REMOTE_DIR": _d("/example/path"),
    "KASSENSTURZ_NEXTCLOUD_REMOTE_FILE": _d("remote_file.xlsx"),
    "KASSENSTURZ_NEXTCLOUD_CA_CERT_PATH": _d(""),
    "KASSENSTURZ_NEXTCLOUD_VERIFY": _d("false"),
}
