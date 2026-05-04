import mimetypes
from pathlib import Path

from flask import Flask

from config import Config
from core.storage_objects.cash_storage import CashStorage
from web.app_paths import AppPaths
from web.kassensturz_web_app import KassensturzWebApp

mimetypes.add_type("application/javascript", ".js")

storage = CashStorage()

__all__ = [
    "AppPaths",
    "Config",
    "KassensturzWebApp",
    "app",
    "create_app",
    "create_web_app",
    "storage",
    "web_app",
]


def _sync_legacy_path_globals(paths: AppPaths):
    globals()["BASE_DIR"] = paths.base_dir
    globals()["DATA_DIR"] = paths.data_dir
    globals()["BACKUP_DIR"] = paths.backup_dir
    globals()["LOCAL_DB_FILE"] = paths.db_file
    globals()["LOCAL_EXCEL_EXPORT_FILE"] = paths.excel_export_file
    globals()["LOCAL_TEXT_EXPORT_FILE"] = paths.text_export_file
    globals()["SYNC_STATE_FILE"] = paths.sync_state_file


def create_web_app(
    *,
    config=Config,
    base_dir: Path | None = None,
    paths: AppPaths | None = None,
) -> KassensturzWebApp:
    return KassensturzWebApp(
        config=config,
        base_dir=base_dir,
        paths=paths,
        legacy_path_sync=_sync_legacy_path_globals,
    )


def create_app(
    *,
    config=Config,
    base_dir: Path | None = None,
    paths: AppPaths | None = None,
) -> Flask:
    return create_web_app(config=config, base_dir=base_dir, paths=paths).flask_app


web_app = create_web_app()
app = web_app.flask_app
_sync_legacy_path_globals(web_app.paths)


if __name__ == "__main__":
    debug = web_app.config.MODE == "debug" and not getattr(
        web_app.config,
        "IS_FROZEN",
        False,
    )
    app.run(debug=debug, use_reloader=debug)
