from base64 import b64decode


def _d(*chunks: str) -> str:
    return b64decode("".join(chunks)).decode("utf-8")


BUNDLED_CONFIG = {
    "KASSENSTURZ_MODE": _d("cHJvZHVjdGlvbg=="),
    "KASSENSTURZ_SECRET_KEY": _d("cmVwbGFjZS1tZQ=="),
    "KASSENSTURZ_ADMIN_PASSWORD": _d("YWRtaW4="),
    "KASSENSTURZ_NEXTCLOUD_BASE_URL": _d(""),
    "KASSENSTURZ_NEXTCLOUD_USERNAME": _d(""),
    "KASSENSTURZ_NEXTCLOUD_APP_PASSWORD": _d(""),
    "KASSENSTURZ_NEXTCLOUD_REMOTE_DIR": _d("QXBwcy9LYXNzZW5zdHVyeg=="),
    "KASSENSTURZ_NEXTCLOUD_REMOTE_FILE": _d("a2Fzc2Vuc3R1cnpfZGF0YS54bHN4"),
    "KASSENSTURZ_NEXTCLOUD_CA_CERT_PATH": _d(""),
    "KASSENSTURZ_NEXTCLOUD_VERIFY": _d("ZmFsc2U="),
}
