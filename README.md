# Kassensturz

![Version](https://img.shields.io/badge/version-v0.2.26-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Kassensturz is a local-first Flask app for tracking cash counts, cash movements,
and current balances across multiple cash accounts.

It is built for small event or venue cash workflows where the important question
is simple: how much cash should be in each box right now, and why?

## Core Model

Kassensturz separates physical truth from money flow.

- A cash count sets the current balance of an account.
- A cash movement moves money between accounts and updates both balances.
- The SQLite database is the local source of truth.
- Excel and text files are exports for sync, inspection, and backup workflows.

Example:

```text
Count:    Bar Cash Box = 200.00 EUR
Movement: Bar Cash Box -> Runner Float = 50.00 EUR

Result:   Bar Cash Box = 150.00 EUR
          Runner Float = 50.00 EUR
```

## Features

- Record opening, closing, spot-check, and reconciliation counts.
- Track movements between cash boxes, floats, suppliers, handouts, and bank.
- Use denomination inputs for bills, coins, and coin rolls.
- View live balances with recent counts and movements.
- Group records by free-text context, such as an event name.
- Export the full dataset to Excel and plain text.
- Optionally sync through Nextcloud WebDAV with append-only remote imports.
- Restore local SQLite backups through the admin view.
- Use English or German UI text with dark and light themes.

## App Structure

The app is organized around explicit objects at the app, service, and storage
boundaries.

```text
app.py
  create_app()

web/
  app_paths.py              AppPaths
  kassensturz_web_app.py    KassensturzWebApp

core/
  cash/                cash workflow request/result/service classes
  storage_objects/     bound storage and repository classes
  storage_accounts.py
  storage_contexts.py
  storage_counts.py
  storage_movements.py
  storage_migrations.py
  storage_connection.py
  cash_export_service.py
  nextcloud_client.py
  sync_state_store.py
  storage.py           compatibility facade for older storage imports
  export_utils.py      Excel and text import/export
  nextcloud_sync.py    WebDAV functions
  sync_state.py        sync metadata functions
  admin_maintenance_service.py
```

Routes create request objects such as `CashCountRequest` and
`CashMovementRequest`. `CashService` applies business rules and runs the sync
pipeline. `CashStorage(db_path)` exposes bound repositories for accounts,
contexts, counts, movements, and backups.

More detail:

- [Developer context](docs/DEV_CONTEXT.md)
- [Import paths](docs/import_paths.md)
- [Data flow](docs/dataflow.md)
- [Configuration and deployment](docs/configuration.md)
- [Changelog](docs/CHANGELOG.md)

## Configuration

`config.py` is tracked and should contain structure plus safe defaults only. Real
secrets must come from environment variables, local ignored files, or the
temporary PyInstaller secrets-module workflow.

Configuration priority:

1. Real environment variables
2. `KASSENSTURZ_ENV_FILE`, source/dev runs only
3. `kassensturz.env`, source/dev runs only
4. `.env`, source/dev runs only
5. Ignored secrets module from `kassensturz_secrets.py`, source/debug and frozen builds
6. Safe defaults from `config.py`

For local development, copy `.env.example` to `kassensturz.env` and fill in the
real values. The debug server can also read an ignored `kassensturz_secrets.py`
fallback, which is useful while the PyInstaller workaround is still in use.

For Docker, inject the same `KASSENSTURZ_*` values through the container
environment or the server platform's secret management.

For the temporary PyInstaller build, generate an ignored secrets module before
building. The same module is also read by the local debug server, and real
environment variables still override it. This lets the portable app run without
a visible config file:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

Bundled config is practical obscurity for trusted users, not cryptographic
protection. The long-term server deployment should keep shared secrets on the
server side.

See [configuration.md](docs/configuration.md) for the full setup notes.

## Local Development

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

For development, tests, linting, and PyInstaller builds, install the dev
dependencies instead:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Create local configuration:

```powershell
Copy-Item .env.example kassensturz.env
```

Run the app:

```powershell
.\venv\Scripts\python.exe app.py
```

By default, development data is stored under `data/debug/`.

## Versioning and Migrations

Application and database schema versions live in `core/version.py`.

SQLite schema migrations use `PRAGMA user_version`. `core/storage_migrations.py`
currently defines schema version `1` as the baseline schema and
`ensure_db_file()` migrates or repairs a database before normal reads and writes
continue.

When production starts with no cash counts or movements, it can bootstrap from
the configured remote Excel file. Both the current Kassensturz export format and
the legacy cash-count columns (`Date`, `Timestamp`, `Event name`, `Counted by`,
`Cash sum`, `Event status`, `Comment`) are supported.

When a schema change is needed, add a new migration function, increment
`DB_SCHEMA_VERSION`, and cover both fresh databases and upgraded databases in
tests.

## Tests

Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m pytest tests
```

Run linting and formatting checks:

```powershell
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m ruff format --check .
```

Or run the combined local check script:

```powershell
.\tools\check.ps1
```

The suite covers storage behavior, schema migrations, service workflows, route
wiring, export/import roundtrips, config loading, and secrets-module generation.

## Portable Build

The current portable build is a temporary workaround until the app can run in the
target Docker/server environment.

Build on Windows:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

Output:

```text
dist/Kassensturz/
```

Run:

```text
Kassensturz.exe
```

## Docker Direction

The preferred deployment path is a server-hosted Docker container. In that setup,
secrets should be configured during container setup and should not be shipped to
desktop users.

Local Docker draft:

```powershell
Copy-Item docker.env.example docker.env
docker compose up --build
```

The compose setup publishes the app on `http://127.0.0.1:5000/` and stores
runtime data in named Docker volumes:

- `kassensturz-data`
- `kassensturz-logs`

Until then, the PyInstaller build can bundle a generated, ignored config module
so trusted users can run the app without handling credentials directly.

## License

MIT License. See [docs/LICENSE](docs/LICENSE).
