import argparse
from base64 import b64encode
from pathlib import Path


CONFIG_KEYS = [
    "KASSENSTURZ_MODE",
    "KASSENSTURZ_PRODUCTION_MODE",
    "KASSENSTURZ_SECRET_KEY",
    "KASSENSTURZ_ADMIN_PASSWORD",
    "KASSENSTURZ_NEXTCLOUD_BASE_URL",
    "KASSENSTURZ_NEXTCLOUD_USERNAME",
    "KASSENSTURZ_NEXTCLOUD_APP_PASSWORD",
    "KASSENSTURZ_NEXTCLOUD_REMOTE_DIR",
    "KASSENSTURZ_NEXTCLOUD_REMOTE_FILE",
    "KASSENSTURZ_NEXTCLOUD_CA_CERT_PATH",
    "KASSENSTURZ_NEXTCLOUD_VERIFY",
]


def strip_optional_quotes(value: str) -> str:
    if len(value) < 2:
        return value

    if value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]

    return value


def read_env_file(path: Path) -> dict[str, str]:
    values = {}
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
        if key in CONFIG_KEYS:
            values[key] = strip_optional_quotes(value.strip())

    return values


def chunked(value: str, size: int = 24) -> list[str]:
    return [value[index : index + size] for index in range(0, len(value), size)] or [""]


def encoded_chunks(value: str) -> str:
    encoded = b64encode(value.encode("utf-8")).decode("ascii")
    return ", ".join(repr(chunk) for chunk in chunked(encoded))


def render_module(values: dict[str, str]) -> str:
    lines = [
        "from base64 import b64decode",
        "from binascii import Error as BinasciiError",
        "",
        "",
        "def _d(*chunks: str) -> str:",
        '    value = "".join(chunks)',
        "    try:",
        '        return b64decode(value).decode("utf-8")',
        "    except (BinasciiError, UnicodeDecodeError):",
        "        return value",
        "",
        "",
        "BUNDLED_CONFIG = {",
    ]

    for key in CONFIG_KEYS:
        if key in values:
            lines.append(f"    {key!r}: _d({encoded_chunks(values[key])}),")

    lines.extend(["}", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Create ignored bundled config for PyInstaller builds."
    )
    parser.add_argument(
        "env_file",
        nargs="?",
        default="kassensturz.env",
        help="Input env file with KASSENSTURZ_* values.",
    )
    parser.add_argument(
        "--output",
        default="kassensturz_secrets.py",
        help="Output Python module included by Kassensturz.spec when present.",
    )
    args = parser.parse_args()

    env_file = Path(args.env_file)
    output = Path(args.output)

    if not env_file.exists():
        raise SystemExit(f"Input env file does not exist: {env_file}")

    values = read_env_file(env_file)
    output.write_text(render_module(values), encoding="utf-8")
    print(f"Wrote {output} with {len(values)} bundled config values.")


if __name__ == "__main__":
    main()
