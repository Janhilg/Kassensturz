import os
import sys
import importlib
from pathlib import Path


def _config_base_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _strip_optional_quotes(value: str) -> str:
    if len(value) < 2:
        return value

    if value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]

    return value


def load_env_file(path: Path, *, override: bool = False) -> dict[str, str]:
    path = Path(path)
    if not path.exists():
        return {}

    loaded = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line.removeprefix("export ").strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_optional_quotes(value.strip())

        if not key:
            continue

        if override or key not in os.environ:
            os.environ[key] = value
            loaded[key] = value

    return loaded


def load_local_env_files() -> dict[str, str]:
    if _is_frozen():
        return {}

    base_dir = _config_base_dir()
    candidates = []

    explicit_env_file = os.getenv("KASSENSTURZ_ENV_FILE", "").strip()
    if explicit_env_file:
        explicit_path = Path(explicit_env_file).expanduser()
        if not explicit_path.is_absolute():
            explicit_path = base_dir / explicit_path
        candidates.append(explicit_path)

    if not _is_frozen():
        candidates.extend(
            [
                base_dir / "kassensturz.env",
                base_dir / ".env",
            ]
        )

    loaded = {}
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        loaded.update(load_env_file(candidate))

    return loaded


LOADED_LOCAL_ENV = load_local_env_files()
BUNDLED_CONFIG = {}


def load_bundled_config() -> dict[str, str]:
    if not _is_frozen():
        return {}

    try:
        module = importlib.import_module("kassensturz_secrets")
    except ImportError:
        return {}

    bundled_config = getattr(module, "BUNDLED_CONFIG", None)
    if bundled_config is None:
        bundled_config = getattr(module, "SECRETS", {})

    return {
        str(key): str(value)
        for key, value in dict(bundled_config).items()
        if str(key).startswith("KASSENSTURZ_")
    }


BUNDLED_CONFIG = load_bundled_config()


def config_value(name: str, default: str = "") -> str:
    return os.getenv(name, BUNDLED_CONFIG.get(name, default))


class Config:
    # =========================
    # Detect PyInstaller build
    # =========================
    IS_FROZEN = getattr(sys, "frozen", False)

    # =========================
    # App Mode / Mode-based path
    # =========================
    _requested_mode = config_value("KASSENSTURZ_MODE", "").strip().lower()
    _production_mode = config_value(
        "KASSENSTURZ_PRODUCTION_MODE",
        "false",
    ).strip().lower()

    # =========================
    # App Mode PyInstaller build
    # =========================
    if IS_FROZEN or _requested_mode == "production" or _production_mode == "true":
        MODE = "production"
    else:
        MODE = "debug"

    PRODUCTION_MODE = "true" if MODE == "production" else "false"
    _default_remote_dir = (
        "Apps/Kassensturz" if MODE == "production" else "Apps/Kassensturz/Debug"
    )
    NEXTCLOUD_REMOTE_DIR = config_value(
        "KASSENSTURZ_NEXTCLOUD_REMOTE_DIR",
        _default_remote_dir,
    )
    NEXTCLOUD_REMOTE_FILE = config_value(
        "KASSENSTURZ_NEXTCLOUD_REMOTE_FILE",
        "kassensturz_data.xlsx",
    )

    # =========================
    # Account types
    # =========================
    ACCOUNT_TYPE_CASH_BOX = "cash_box"
    ACCOUNT_TYPE_FLOAT = "float"
    ACCOUNT_TYPE_BANK = "bank"
    ACCOUNT_TYPE_EXTERNAL_SINK = "external_sink"

    ACCOUNT_TYPES = [
        ACCOUNT_TYPE_CASH_BOX,
        ACCOUNT_TYPE_FLOAT,
        ACCOUNT_TYPE_EXTERNAL_SINK,
        ACCOUNT_TYPE_BANK,
    ]

    # =========================
    # Count types
    # =========================
    COUNT_TYPE_OPENING = "opening"
    COUNT_TYPE_CLOSING = "closing"
    COUNT_TYPE_SPOT_CHECK = "spot_check"
    COUNT_TYPE_RECONCILIATION = "reconciliation"

    COUNT_TYPES = [
        COUNT_TYPE_OPENING,
        COUNT_TYPE_CLOSING,
        COUNT_TYPE_SPOT_CHECK,
        COUNT_TYPE_RECONCILIATION,
    ]

    # =========================
    # Default cash accounts
    # IMPORTANT:
    # IDs must stay stable across devices for sync.
    # =========================
    DEFAULT_CASH_ACCOUNTS = [
        ("acc_bar_cash_box", "Bar Cash Box", ACCOUNT_TYPE_CASH_BOX, 20),
        ("acc_entrance_cash_box", "Entrance Cash Box", ACCOUNT_TYPE_CASH_BOX, 30),
        ("acc_runner_float", "Runner Float", ACCOUNT_TYPE_FLOAT, 40),
        ("acc_supplier_drinks", "Supplier / Drinks Purchase", ACCOUNT_TYPE_EXTERNAL_SINK, 50),
        ("acc_handout", "Cash Handout", ACCOUNT_TYPE_EXTERNAL_SINK, 60),
        ("acc_bank", "Bank", ACCOUNT_TYPE_BANK, 70),
    ]

    # =========================
    # Nextcloud credentials
    # =========================
    NEXTCLOUD_BASE_URL = config_value("KASSENSTURZ_NEXTCLOUD_BASE_URL", "")
    NEXTCLOUD_USERNAME = config_value("KASSENSTURZ_NEXTCLOUD_USERNAME", "")
    NEXTCLOUD_APP_PASSWORD = config_value("KASSENSTURZ_NEXTCLOUD_APP_PASSWORD", "")

    # =========================
    # SSL handling
    # =========================
    # unused - does require to get a valid cert
    NEXTCLOUD_CA_CERT_PATH = config_value("KASSENSTURZ_NEXTCLOUD_CA_CERT_PATH", "")
    NEXTCLOUD_VERIFY = config_value("KASSENSTURZ_NEXTCLOUD_VERIFY", "false")

    # =========================
    # Flask Key
    # =========================
    SECRET_KEY = config_value("KASSENSTURZ_SECRET_KEY", "dev-secret-change-me")

    # =========================
    # Admin page password
    # =========================
    ADMIN_PASSWORD = config_value("KASSENSTURZ_ADMIN_PASSWORD", "")
