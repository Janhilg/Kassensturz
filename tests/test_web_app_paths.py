from pathlib import Path

import web.app_paths as app_paths


def test_default_base_dir_uses_executable_parent_when_frozen(monkeypatch):
    executable = Path("C:/portable/Kassensturz/Kassensturz.exe")

    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str(executable))

    assert app_paths.default_base_dir() == executable.parent


def test_bundled_resource_base_dir_uses_pyinstaller_meipass(monkeypatch, tmp_path):
    bundle_dir = tmp_path / "_internal"

    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "_MEIPASS", str(bundle_dir), raising=False)

    assert app_paths.bundled_resource_base_dir() == bundle_dir.resolve()
