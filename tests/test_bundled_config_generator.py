from tools.create_bundled_config import read_env_file, render_module


def test_read_env_file_keeps_only_kassensturz_config(tmp_path):
    env_file = tmp_path / "kassensturz.env"
    env_file.write_text(
        "\n".join(
            [
                "KASSENSTURZ_ADMIN_PASSWORD=admin-secret",
                "OTHER_SECRET=ignored",
            ]
        ),
        encoding="utf-8",
    )

    assert read_env_file(env_file) == {"KASSENSTURZ_ADMIN_PASSWORD": "admin-secret"}


def test_render_module_obscures_plain_values_but_loads_them():
    source = render_module(
        {
            "KASSENSTURZ_ADMIN_PASSWORD": "admin-secret",
        }
    )
    namespace = {}

    exec(source, namespace)

    assert "admin-secret" not in source
    assert namespace["BUNDLED_CONFIG"]["KASSENSTURZ_ADMIN_PASSWORD"] == "admin-secret"
