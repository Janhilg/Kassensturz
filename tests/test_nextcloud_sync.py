from types import SimpleNamespace

import pytest

from core import nextcloud_sync


class Response:
    def __init__(self, status_code, text="", content=b""):
        self.status_code = status_code
        self.text = text
        self.content = content


def _config(**overrides):
    values = {
        "NEXTCLOUD_BASE_URL": "https://cloud.example.test/base/",
        "NEXTCLOUD_USERNAME": "jan hil",
        "NEXTCLOUD_APP_PASSWORD": "secret",
        "NEXTCLOUD_REMOTE_DIR": "Apps/Kassensturz Debug",
        "NEXTCLOUD_REMOTE_FILE": "kassensturz data.xlsx",
        "NEXTCLOUD_VERIFY": "true",
        "NEXTCLOUD_CA_CERT_PATH": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_nextcloud_configuration_and_verify_settings(tmp_path):
    assert nextcloud_sync.nextcloud_configured(_config()) is True
    assert nextcloud_sync.nextcloud_configured(_config(NEXTCLOUD_USERNAME="")) is False
    assert nextcloud_sync.get_verify_setting(_config(NEXTCLOUD_VERIFY="false"), tmp_path) is False
    assert nextcloud_sync.get_verify_setting(_config(), tmp_path) is True

    relative_config = _config(NEXTCLOUD_CA_CERT_PATH="certs/ca.pem")
    assert nextcloud_sync.get_verify_setting(relative_config, tmp_path) == str(
        tmp_path / "certs" / "ca.pem"
    )

    absolute_cert_path = tmp_path / "absolute-ca.pem"
    absolute_config = _config(NEXTCLOUD_CA_CERT_PATH=str(absolute_cert_path))
    assert nextcloud_sync.get_verify_setting(absolute_config, tmp_path) == str(absolute_cert_path)


def test_build_webdav_url_encodes_user_and_path_segments():
    url = nextcloud_sync.build_webdav_url(
        "https://cloud.example.test/",
        "jan hil",
        "/Apps/Kassensturz Debug/kassensturz data.xlsx",
    )

    assert url == (
        "https://cloud.example.test/remote.php/dav/files/"
        "jan%20hil/Apps/Kassensturz%20Debug/kassensturz%20data.xlsx"
    )


def test_ensure_nextcloud_folder_creates_each_path_segment(monkeypatch, tmp_path):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs["auth"], kwargs["verify"]))
        return Response(201)

    monkeypatch.setattr(nextcloud_sync.requests, "request", fake_request)

    nextcloud_sync.ensure_nextcloud_folder(
        _config(NEXTCLOUD_REMOTE_DIR="/Apps/Kassensturz Debug/Production/"),
        tmp_path,
    )

    assert [call[0] for call in calls] == ["MKCOL", "MKCOL", "MKCOL"]
    assert calls[-1][1].endswith("/Apps/Kassensturz%20Debug/Production")
    assert calls[-1][2] == ("jan hil", "secret")
    assert calls[-1][3] is True


def test_ensure_nextcloud_folder_skips_when_unconfigured(monkeypatch, tmp_path):
    def fail_request(*args, **kwargs):
        raise AssertionError("request should not be called")

    monkeypatch.setattr(nextcloud_sync.requests, "request", fail_request)

    nextcloud_sync.ensure_nextcloud_folder(_config(NEXTCLOUD_APP_PASSWORD=""), tmp_path)


def test_ensure_nextcloud_folder_raises_on_unexpected_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        nextcloud_sync.requests,
        "request",
        lambda *args, **kwargs: Response(500, "server error"),
    )

    with pytest.raises(RuntimeError, match="Failed to create Nextcloud folder"):
        nextcloud_sync.ensure_nextcloud_folder(_config(), tmp_path)


def test_download_remote_excel_to_temp_writes_successful_response(monkeypatch, tmp_path):
    requests = []

    def fake_get(url, **kwargs):
        requests.append((url, kwargs))
        return Response(200, content=b"excel-bytes")

    monkeypatch.setattr(nextcloud_sync.requests, "get", fake_get)
    temp_path = tmp_path / "downloads" / "remote.xlsx"

    downloaded = nextcloud_sync.download_remote_excel_to_temp(
        config=_config(),
        base_dir=tmp_path,
        temp_path=temp_path,
    )

    assert downloaded is True
    assert temp_path.read_bytes() == b"excel-bytes"
    assert requests[0][0].endswith("/Apps/Kassensturz%20Debug/kassensturz%20data.xlsx")
    assert requests[0][1]["auth"] == ("jan hil", "secret")


def test_download_remote_excel_to_temp_handles_missing_or_failed_remote(monkeypatch, tmp_path):
    monkeypatch.setattr(
        nextcloud_sync.requests,
        "get",
        lambda *args, **kwargs: Response(404, "not found"),
    )
    assert (
        nextcloud_sync.download_remote_excel_to_temp(
            config=_config(),
            base_dir=tmp_path,
            temp_path=tmp_path / "missing.xlsx",
        )
        is False
    )

    monkeypatch.setattr(
        nextcloud_sync.requests,
        "get",
        lambda *args, **kwargs: Response(503, "unavailable"),
    )
    with pytest.raises(RuntimeError, match="Failed to download Excel file"):
        nextcloud_sync.download_remote_excel_to_temp(
            config=_config(),
            base_dir=tmp_path,
            temp_path=tmp_path / "failed.xlsx",
        )


def test_download_remote_excel_if_exists_replaces_local_file(monkeypatch, tmp_path):
    def fake_download_remote_excel_to_temp(*, config, base_dir, temp_path):
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(b"remote-content")
        return True

    monkeypatch.setattr(
        nextcloud_sync,
        "download_remote_excel_to_temp",
        fake_download_remote_excel_to_temp,
    )
    local_excel_path = tmp_path / "local.xlsx"
    local_excel_path.write_bytes(b"local-content")

    downloaded = nextcloud_sync.download_remote_excel_if_exists(local_excel_path, _config())

    assert downloaded is True
    assert local_excel_path.read_bytes() == b"remote-content"
    assert not (tmp_path / ".local.remote.tmp.xlsx").exists()


def test_download_remote_excel_if_exists_returns_false_without_remote(monkeypatch, tmp_path):
    monkeypatch.setattr(
        nextcloud_sync,
        "download_remote_excel_to_temp",
        lambda **kwargs: False,
    )

    assert (
        nextcloud_sync.download_remote_excel_if_exists(tmp_path / "local.xlsx", _config()) is False
    )


def test_upload_file_to_nextcloud_handles_unconfigured_and_missing_files(tmp_path):
    result = nextcloud_sync.upload_file_to_nextcloud(
        config=_config(NEXTCLOUD_BASE_URL=""),
        base_dir=tmp_path,
        file_path=tmp_path / "missing.xlsx",
        remote_filename="missing.xlsx",
        content_type="application/octet-stream",
    )

    assert result == {
        "uploaded": False,
        "reason": "nextcloud_not_configured",
        "file": "missing.xlsx",
    }

    with pytest.raises(FileNotFoundError):
        nextcloud_sync.upload_file_to_nextcloud(
            config=_config(),
            base_dir=tmp_path,
            file_path=tmp_path / "missing.xlsx",
            remote_filename="missing.xlsx",
            content_type="application/octet-stream",
        )


def test_upload_file_to_nextcloud_puts_file_content(monkeypatch, tmp_path):
    calls = []

    def fake_ensure_nextcloud_folder(config, base_dir):
        calls.append(("ensure_folder", base_dir))

    def fake_put(url, data, **kwargs):
        calls.append(("put", url, data.read(), kwargs["headers"], kwargs["auth"]))
        return Response(201, "created")

    monkeypatch.setattr(nextcloud_sync, "ensure_nextcloud_folder", fake_ensure_nextcloud_folder)
    monkeypatch.setattr(nextcloud_sync.requests, "put", fake_put)
    file_path = tmp_path / "export.xlsx"
    file_path.write_bytes(b"workbook")

    result = nextcloud_sync.upload_file_to_nextcloud(
        config=_config(),
        base_dir=tmp_path,
        file_path=file_path,
        remote_filename="remote name.xlsx",
        content_type="application/vnd.test",
    )

    assert result == {
        "uploaded": True,
        "file": "export.xlsx",
        "remote_path": "Apps/Kassensturz Debug/remote name.xlsx",
        "size_bytes": 8,
    }
    assert calls[0] == ("ensure_folder", tmp_path)
    assert calls[1][0] == "put"
    assert calls[1][1].endswith("/Apps/Kassensturz%20Debug/remote%20name.xlsx")
    assert calls[1][2] == b"workbook"
    assert calls[1][3] == {"Content-Type": "application/vnd.test"}
    assert calls[1][4] == ("jan hil", "secret")


def test_upload_file_to_nextcloud_raises_on_failed_put(monkeypatch, tmp_path):
    monkeypatch.setattr(nextcloud_sync, "ensure_nextcloud_folder", lambda *args: None)
    monkeypatch.setattr(
        nextcloud_sync.requests,
        "put",
        lambda *args, **kwargs: Response(500, "upload failed"),
    )
    file_path = tmp_path / "export.xlsx"
    file_path.write_bytes(b"workbook")

    with pytest.raises(RuntimeError, match="Failed to upload file"):
        nextcloud_sync.upload_file_to_nextcloud(
            config=_config(),
            base_dir=tmp_path,
            file_path=file_path,
            remote_filename="remote.xlsx",
            content_type="application/vnd.test",
        )


def test_upload_wrappers_use_expected_remote_names(monkeypatch, tmp_path):
    calls = []

    def fake_upload_file_to_nextcloud(**kwargs):
        calls.append(kwargs)
        return {"uploaded": True, "remote_filename": kwargs["remote_filename"]}

    monkeypatch.setattr(nextcloud_sync, "upload_file_to_nextcloud", fake_upload_file_to_nextcloud)
    excel_path = tmp_path / "export.xlsx"
    text_path = tmp_path / "export.txt"
    config = _config(NEXTCLOUD_REMOTE_FILE="cash-data.xlsx")

    excel_result = nextcloud_sync.upload_excel_file_to_nextcloud(config, tmp_path, excel_path)
    text_result = nextcloud_sync.upload_text_file_to_nextcloud(config, tmp_path, text_path)

    assert excel_result["remote_filename"] == "cash-data.xlsx"
    assert text_result["remote_filename"] == "cash-data.txt"
    assert calls[0]["content_type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert calls[1]["content_type"] == "text/plain; charset=utf-8"


def test_upload_files_combines_excel_and_text_results(monkeypatch, tmp_path):
    def fake_upload_excel_file_to_nextcloud(config, base_dir, file_path):
        return {"uploaded": True, "file": file_path.name}

    def fake_upload_text_file_to_nextcloud(config, base_dir, file_path):
        return {"uploaded": True, "file": file_path.name}

    monkeypatch.setattr(
        nextcloud_sync,
        "upload_excel_file_to_nextcloud",
        fake_upload_excel_file_to_nextcloud,
    )
    monkeypatch.setattr(
        nextcloud_sync,
        "upload_text_file_to_nextcloud",
        fake_upload_text_file_to_nextcloud,
    )

    assert nextcloud_sync.upload_files(
        excel_path=tmp_path / "export.xlsx",
        text_path=tmp_path / "export.txt",
        config=_config(),
    ) == {
        "excel": {"uploaded": True, "file": "export.xlsx"},
        "text": {"uploaded": True, "file": "export.txt"},
    }


def test_nextcloud_sync_legacy_getattr_exports_client_class():
    assert nextcloud_sync.NextcloudClient.__name__ == "NextcloudClient"

    missing_name = "not_a_real_export"
    with pytest.raises(AttributeError):
        getattr(nextcloud_sync, missing_name)
