import logging
import sys
from pathlib import Path
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


def _default_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


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
    return all(
        [
            getattr(config, "NEXTCLOUD_BASE_URL", ""),
            getattr(config, "NEXTCLOUD_USERNAME", ""),
            getattr(config, "NEXTCLOUD_APP_PASSWORD", ""),
        ]
    )


def build_webdav_url(base_url: str, username: str, path: str) -> str:
    encoded_path = "/".join(quote(part) for part in path.strip("/").split("/"))
    return f"{base_url.rstrip('/')}/remote.php/dav/files/{quote(username)}/{encoded_path}"


def ensure_nextcloud_folder(config, base_dir: Path):
    if not nextcloud_configured(config):
        logger.info("Nextcloud not configured; skipping folder creation")
        return

    parts = [part for part in config.NEXTCLOUD_REMOTE_DIR.strip("/").split("/") if part]
    current_path = ""

    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part

        response = requests.request(
            "MKCOL",
            build_webdav_url(
                config.NEXTCLOUD_BASE_URL,
                config.NEXTCLOUD_USERNAME,
                current_path,
            ),
            auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
            timeout=30,
            verify=get_verify_setting(config, base_dir),
        )

        if response.status_code not in (201, 405):
            raise RuntimeError(
                f"Failed to create Nextcloud folder '{current_path}': "
                f"{response.status_code} {response.text}"
            )

    logger.info("Nextcloud folder ensured | remote_dir=%s", config.NEXTCLOUD_REMOTE_DIR)


def download_remote_excel_to_temp(config, base_dir: Path, temp_path: Path) -> bool:
    if not nextcloud_configured(config):
        logger.info("Nextcloud not configured; skipping remote Excel download")
        return False

    remote_path = f"{config.NEXTCLOUD_REMOTE_DIR}/{config.NEXTCLOUD_REMOTE_FILE}"
    logger.info("Downloading remote Excel | remote_path=%s", remote_path)

    response = requests.get(
        build_webdav_url(
            config.NEXTCLOUD_BASE_URL,
            config.NEXTCLOUD_USERNAME,
            remote_path,
        ),
        auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
        timeout=60,
        verify=get_verify_setting(config, base_dir),
    )

    if response.status_code == 200:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(response.content)
        size = temp_path.stat().st_size
        logger.info(
            "Downloaded remote Excel | path=%s size=%s (%s)",
            temp_path,
            size,
            f"{size / 1024:.1f} KB",
        )
        return True

    if response.status_code == 404:
        logger.info("Remote Excel does not exist | remote_path=%s", remote_path)
        return False

    raise RuntimeError(
        f"Failed to download Excel file from Nextcloud: {response.status_code} {response.text}"
    )


def download_remote_excel_if_exists(local_excel_path: Path, config) -> bool:
    """
    Service-layer wrapper expected by cash_service.py.

    Downloads the remote Excel into a temporary file first, then replaces the
    provided local file if the remote exists.

    Returns:
        True if the remote file existed and was downloaded.
        False if no remote file exists or Nextcloud is not configured.
    """
    base_dir = _default_base_dir()
    temp_path = (
        local_excel_path.parent / f".{local_excel_path.stem}.remote.tmp{local_excel_path.suffix}"
    )

    try:
        downloaded = download_remote_excel_to_temp(
            config=config,
            base_dir=base_dir,
            temp_path=temp_path,
        )

        if not downloaded:
            return False

        local_excel_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(local_excel_path)

        logger.info(
            "Remote Excel moved into local path | local_path=%s",
            local_excel_path,
        )
        return True

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                logger.exception("Failed to clean up temp download | path=%s", temp_path)


def upload_file_to_nextcloud(
    *,
    config,
    base_dir: Path,
    file_path: Path,
    remote_filename: str,
    content_type: str,
):
    if not nextcloud_configured(config):
        logger.info("Nextcloud not configured; skipping upload | file=%s", file_path)
        return {
            "uploaded": False,
            "reason": "nextcloud_not_configured",
            "file": file_path.name,
        }

    if not file_path.exists():
        raise FileNotFoundError(f"Cannot upload missing file: {file_path}")

    file_size = file_path.stat().st_size
    logger.info(
        "Uploading file | name=%s size=%s (%s)",
        file_path.name,
        file_size,
        f"{file_size / 1024:.1f} KB",
    )

    ensure_nextcloud_folder(config, base_dir)

    remote_path = f"{config.NEXTCLOUD_REMOTE_DIR}/{remote_filename}"
    url = build_webdav_url(
        config.NEXTCLOUD_BASE_URL,
        config.NEXTCLOUD_USERNAME,
        remote_path,
    )

    logger.info("Uploading to remote path | remote_path=%s", remote_path)
    logger.debug("WebDAV URL | url=%s", url)

    with file_path.open("rb") as file_handle:
        response = requests.put(
            url,
            data=file_handle,
            auth=(config.NEXTCLOUD_USERNAME, config.NEXTCLOUD_APP_PASSWORD),
            headers={"Content-Type": content_type},
            timeout=60,
            verify=get_verify_setting(config, base_dir),
        )

    logger.debug("Upload response | status=%s", response.status_code)
    logger.debug("Upload response body | body=%s", response.text[:500])

    if response.status_code not in (200, 201, 204):
        logger.error(
            "Failed to upload file | status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(
            f"Failed to upload file to Nextcloud: {response.status_code} {response.text}"
        )

    logger.info(
        "Upload completed | name=%s size=%s remote_path=%s",
        file_path.name,
        file_size,
        remote_path,
    )

    return {
        "uploaded": True,
        "file": file_path.name,
        "remote_path": remote_path,
        "size_bytes": file_size,
    }


def upload_excel_file_to_nextcloud(config, base_dir: Path, file_path: Path):
    return upload_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=file_path,
        remote_filename=config.NEXTCLOUD_REMOTE_FILE,
        content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    )


def upload_text_file_to_nextcloud(config, base_dir: Path, file_path: Path):
    remote_txt_filename = Path(config.NEXTCLOUD_REMOTE_FILE).with_suffix(".txt").name
    return upload_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=file_path,
        remote_filename=remote_txt_filename,
        content_type="text/plain; charset=utf-8",
    )


def upload_files(excel_path: Path, text_path: Path, config):
    """
    Service-layer wrapper expected by cash_service.py.
    Uploads both Excel and text exports and returns a combined summary.
    """
    base_dir = _default_base_dir()

    excel_result = upload_excel_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=excel_path,
    )
    text_result = upload_text_file_to_nextcloud(
        config=config,
        base_dir=base_dir,
        file_path=text_path,
    )

    combined = {
        "excel": excel_result,
        "text": text_result,
    }

    logger.info("Upload summary | %s", combined)
    return combined


class NextcloudClient:
    get_verify_setting = staticmethod(get_verify_setting)
    nextcloud_configured = staticmethod(nextcloud_configured)
    build_webdav_url = staticmethod(build_webdav_url)
    ensure_nextcloud_folder = staticmethod(ensure_nextcloud_folder)
    download_remote_excel_to_temp = staticmethod(download_remote_excel_to_temp)
    download_remote_excel_if_exists = staticmethod(download_remote_excel_if_exists)
    upload_file_to_nextcloud = staticmethod(upload_file_to_nextcloud)
    upload_excel_file_to_nextcloud = staticmethod(upload_excel_file_to_nextcloud)
    upload_text_file_to_nextcloud = staticmethod(upload_text_file_to_nextcloud)
    upload_files = staticmethod(upload_files)
