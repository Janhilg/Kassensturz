import requests
import logging
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)


def get_verify_setting(config, base_dir: Path):
    if getattr(config, "NEXTCLOUD_VERIFY", "true").lower() == "false":
        return False

    ca_cert_path = getattr(config, "NEXTCLOUD_CA_CERT_PATH", "")
    if ca_cert_path:
        ca_path = Path(ca_cert_path)
        if not ca_path.is_absolute():
            ca_path = base_dir / ca_path
        return str(ca_path)

    return True


def nextcloud_configured(config) -> bool:
    return all([
        config.NEXTCLOUD_BASE_URL,
        config.NEXTCLOUD_USERNAME,
        config.NEXTCLOUD_APP_PASSWORD,
    ])


def build_webdav_url(base_url: str, username: str, path: str) -> str:
    encoded_path = "/".join(quote(part) for part in path.strip("/").split("/"))
    return (
        f"{base_url.rstrip('/')}/remote.php/dav/files/"
        f"{quote(username)}/{encoded_path}"
    )


def ensure_nextcloud_folder(config, base_dir: Path):
    if not nextcloud_configured(config):
        return

    parts = [part for part in config.NEXTCLOUD_REMOTE_DIR.strip("/").split("/") if part]
    current_path = ""

    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part
        response = requests.request(
            "MKCOL",
            build_webdav_url(config.NEXTCLOUD_BASE_URL, config.NEXTCLOUD_USERNAME, current_path),
            auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
            timeout=30,
            verify=get_verify_setting(config, base_dir),
        )

        if response.status_code not in (201, 405):
            raise RuntimeError(
                f"Failed to create Nextcloud folder '{current_path}': "
                f"{response.status_code} {response.text}"
            )


def download_remote_excel_to_temp(config, base_dir: Path, temp_path: Path) -> bool:
    if not nextcloud_configured(config):
        return False

    remote_path = f"{config.NEXTCLOUD_REMOTE_DIR}/{config.NEXTCLOUD_REMOTE_FILE}"
    response = requests.get(
        build_webdav_url(config.NEXTCLOUD_BASE_URL, config.NEXTCLOUD_USERNAME, remote_path),
        auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
        timeout=60,
        verify=get_verify_setting(config, base_dir),
    )

    if response.status_code == 200:
        temp_path.write_bytes(response.content)

        size = temp_path.stat().st_size
        logger.info(
            "Downloaded remote Excel | size=%s (%s)",
            size,
            f"{size / 1024:.1f} KB"
        )

        return True

    if response.status_code == 404:
        return False

    raise RuntimeError(
        f"Failed to download Excel file from Nextcloud: "
        f"{response.status_code} {response.text}"
    )


def upload_file_to_nextcloud(
    *,
    config,
    base_dir: Path,
    file_path: Path,
    remote_filename: str,
    content_type: str,
):
    if not nextcloud_configured(config):
        return

    file_size = file_path.stat().st_size

    logger.info(
        "Uploading file | name=%s size=%s (%s)",
        file_path.name,
        file_size,
        f"{file_size / 1024:.1f} KB"
    )

    ensure_nextcloud_folder(config, base_dir)

    remote_path = f"{config.NEXTCLOUD_REMOTE_DIR}/{remote_filename}"
    url = build_webdav_url(config.NEXTCLOUD_BASE_URL, config.NEXTCLOUD_USERNAME, remote_path)

    logger.info(f"Uploading to: {remote_path}")
    logger.info(f"WebDAV URL: {url}")

    with file_path.open("rb") as file_handle:
        response = requests.put(
            url,
            data=file_handle,
            auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
            headers={"Content-Type": content_type},
            timeout=60,
            verify=get_verify_setting(config, base_dir),
        )

    logger.debug(f"Upload response: {response.status_code}")
    logger.debug(f"Upload response body: {response.text[:500]}")

    if response.status_code not in (200, 201, 204):
        logger.error(f"Failed to upload file to Nextcloud {response.status_code} {response.text}")
        raise RuntimeError(
            f"Failed to upload file to Nextcloud: "
            f"{response.status_code} {response.text}"
        )
    logger.info(
        "Upload completed | name=%s size=%s",
        file_path.name,
        file_size
    )


def upload_excel_file_to_nextcloud(config, base_dir: Path, file_path: Path):
    upload_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=file_path,
        remote_filename=config.NEXTCLOUD_REMOTE_FILE,
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


def upload_text_file_to_nextcloud(config, base_dir: Path, file_path: Path):
    remote_txt_filename = Path(config.NEXTCLOUD_REMOTE_FILE).with_suffix(".txt").name
    upload_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=file_path,
        remote_filename=remote_txt_filename,
        content_type="text/plain; charset=utf-8",
    )