import os
import sys
from types import SimpleNamespace

import config as config_module
from config import load_env_file


def test_load_env_file_sets_missing_values_without_overriding_existing_env(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / "kassensturz.env"
    env_file.write_text(
        "\n".join(
            [
                "# local secrets",
                "KASSENSTURZ_SECRET_KEY=file-secret",
                'export KASSENSTURZ_ADMIN_PASSWORD="file-admin"',
                "BROKEN_LINE",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KASSENSTURZ_SECRET_KEY", "real-env-secret")
    monkeypatch.delenv("KASSENSTURZ_ADMIN_PASSWORD", raising=False)

    loaded = load_env_file(env_file)

    assert os.environ["KASSENSTURZ_SECRET_KEY"] == "real-env-secret"
    assert os.environ["KASSENSTURZ_ADMIN_PASSWORD"] == "file-admin"
    assert loaded == {"KASSENSTURZ_ADMIN_PASSWORD": "file-admin"}


def test_load_local_env_files_supports_explicit_relative_file(tmp_path, monkeypatch):
    env_file = tmp_path / "portable.env"
    env_file.write_text("KASSENSTURZ_ADMIN_PASSWORD=portable-admin", encoding="utf-8")
    monkeypatch.setattr(config_module, "_config_base_dir", lambda: tmp_path)
    monkeypatch.setenv("KASSENSTURZ_ENV_FILE", "portable.env")
    monkeypatch.delenv("KASSENSTURZ_ADMIN_PASSWORD", raising=False)

    loaded = config_module.load_local_env_files()

    assert loaded == {"KASSENSTURZ_ADMIN_PASSWORD": "portable-admin"}
    assert os.environ["KASSENSTURZ_ADMIN_PASSWORD"] == "portable-admin"


def test_load_local_env_files_skips_all_files_for_frozen_app(tmp_path, monkeypatch):
    env_file = tmp_path / "kassensturz.env"
    env_file.write_text("KASSENSTURZ_ADMIN_PASSWORD=should-not-load", encoding="utf-8")
    explicit_env_file = tmp_path / "explicit.env"
    explicit_env_file.write_text(
        "KASSENSTURZ_SECRET_KEY=should-not-load",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_config_base_dir", lambda: tmp_path)
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setenv("KASSENSTURZ_ENV_FILE", str(explicit_env_file))
    monkeypatch.delenv("KASSENSTURZ_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("KASSENSTURZ_SECRET_KEY", raising=False)

    loaded = config_module.load_local_env_files()

    assert loaded == {}
    assert "KASSENSTURZ_ADMIN_PASSWORD" not in os.environ
    assert "KASSENSTURZ_SECRET_KEY" not in os.environ


def test_load_bundled_config_reads_generated_module_only_when_frozen(monkeypatch):
    fake_module = SimpleNamespace(
        BUNDLED_CONFIG={
            "KASSENSTURZ_ADMIN_PASSWORD": "bundled-admin",
            "IGNORED_KEY": "ignored",
        }
    )
    monkeypatch.setitem(sys.modules, "kassensturz_secrets", fake_module)
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)

    assert config_module.load_bundled_config() == {"KASSENSTURZ_ADMIN_PASSWORD": "bundled-admin"}


def test_config_value_prefers_environment_over_bundled_config(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "BUNDLED_CONFIG",
        {"KASSENSTURZ_ADMIN_PASSWORD": "bundled-admin"},
    )
    monkeypatch.setenv("KASSENSTURZ_ADMIN_PASSWORD", "env-admin")

    assert config_module.config_value("KASSENSTURZ_ADMIN_PASSWORD") == "env-admin"


def test_config_value_uses_bundled_config_before_default(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "BUNDLED_CONFIG",
        {"KASSENSTURZ_ADMIN_PASSWORD": "bundled-admin"},
    )
    monkeypatch.delenv("KASSENSTURZ_ADMIN_PASSWORD", raising=False)

    assert config_module.config_value("KASSENSTURZ_ADMIN_PASSWORD") == "bundled-admin"
