from base64 import b64decode
from binascii import Error as BinasciiError

# Copy or generate this file as ignored kassensturz_secrets.py for local
# source/debug runs and the temporary PyInstaller build.


def _d(*chunks: str) -> str:
    value = "".join(chunks)
    try:
        return b64decode(value).decode("utf-8")
    except (BinasciiError, UnicodeDecodeError):
        return value


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
