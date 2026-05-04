# Configuration and Deployment

This page describes how Kassensturz receives runtime configuration and how secrets should be handled in development, PyInstaller builds, and Docker deployments.

## Configuration Priority

Configuration is resolved in this order:

1. Real environment variables
2. `KASSENSTURZ_ENV_FILE`, source/dev runs only
3. `kassensturz.env`, source/dev runs only
4. `.env`, source/dev runs only
5. Bundled PyInstaller config from `kassensturz_secrets.py`, frozen builds only
6. Safe defaults from `config.py`

Environment variables always win.

## Tracked Files

These files are safe to commit:

- `config.py`: structure and safe defaults only
- `.env.example`: names of supported settings and placeholder values
- `docker.env.example`: Docker-oriented placeholder settings
- `kassensturz_secrets.example.py`: example bundled config module with placeholder values
- `tools/create_bundled_config.py`: generator for local PyInstaller builds

These files must not be committed:

- `.env`
- `docker.env`
- `kassensturz.env`
- `kassensturz_secrets.py`
- any file containing real Nextcloud credentials, admin passwords, or Flask secret keys

## Supported Settings

```text
KASSENSTURZ_MODE
KASSENSTURZ_PRODUCTION_MODE
KASSENSTURZ_SECRET_KEY
KASSENSTURZ_ADMIN_PASSWORD
KASSENSTURZ_NEXTCLOUD_BASE_URL
KASSENSTURZ_NEXTCLOUD_USERNAME
KASSENSTURZ_NEXTCLOUD_APP_PASSWORD
KASSENSTURZ_NEXTCLOUD_REMOTE_DIR
KASSENSTURZ_NEXTCLOUD_REMOTE_FILE
KASSENSTURZ_NEXTCLOUD_CA_CERT_PATH
KASSENSTURZ_NEXTCLOUD_VERIFY
```

## Local Development

Create a local env file from the example:

```powershell
Copy-Item .env.example kassensturz.env
```

Then fill in the real values in `kassensturz.env`.

The app loads `kassensturz.env` automatically when running from source. Real environment variables override values from the file.

## Temporary PyInstaller Build

The PyInstaller build should work out of the box without a visible config file next to the executable.

Generate the ignored bundled config module before building:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

`Kassensturz.spec` includes `kassensturz_secrets.py` only when that ignored local file exists.

The generated module stores values base64-encoded. This prevents casual viewing in a plain config file and keeps secrets out of Git. It is not cryptographic protection against reverse engineering.

Use this for the current trusted-user portable app workaround. The long-term server deployment should use environment variables or secret management instead.

## Docker Deployment

For Docker, do not use bundled PyInstaller config.

Inject settings through the container environment, an `env_file`, or the server platform's secret management.

Local draft setup:

```powershell
Copy-Item docker.env.example docker.env
docker compose up --build
```

The draft compose file:

- builds the local image from `Dockerfile`
- runs Gunicorn on port `5000`
- reads secrets and environment-specific values from ignored `docker.env`
- stores SQLite data and exports in the `kassensturz-data` named volume
- stores logs in the `kassensturz-logs` named volume
- exposes `http://127.0.0.1:5000/`

The app data path inside the container is `/app/data`.

Server-side example:

```yaml
services:
  kassensturz:
    image: kassensturz:latest
    environment:
      KASSENSTURZ_MODE: production
      KASSENSTURZ_NEXTCLOUD_BASE_URL: https://example.invalid/
      KASSENSTURZ_NEXTCLOUD_USERNAME: kasse@example.invalid
      KASSENSTURZ_NEXTCLOUD_APP_PASSWORD: ${KASSENSTURZ_NEXTCLOUD_APP_PASSWORD}
      KASSENSTURZ_SECRET_KEY: ${KASSENSTURZ_SECRET_KEY}
      KASSENSTURZ_ADMIN_PASSWORD: ${KASSENSTURZ_ADMIN_PASSWORD}
```

In the Docker/server scenario, the server owns the secrets. Users should not receive them in a desktop bundle.

## Practical Security Model

For the current PyInstaller workaround, the goal is to avoid accidental disclosure:

- no secrets in Git
- no secrets in `config.py`
- no visible env/config file shipped next to the executable
- app starts with bundled values for trusted users

For stronger protection, move the sensitive sync operation behind a server-side API. The client should authenticate to your app, and the server should own the Nextcloud credentials.
