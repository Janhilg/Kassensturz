# Kassensturz

![Version](https://img.shields.io/badge/version-v0.2.2-blue)
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
  KassensturzWebApp
  AppPaths
  create_app()

core/
  cash_service.py      business workflows and sync orchestration
  storage.py           SQLite functions plus bound repositories
  export_utils.py      Excel and text import/export
  nextcloud_sync.py    WebDAV transport
  sync_state.py        sync metadata
  admin_service.py     admin maintenance helpers
```

Routes create request objects such as `CashCountRequest` and
`CashMovementRequest`. `CashService` applies business rules and runs the sync
pipeline. `CashStorage(db_path)` exposes bound repositories for accounts,
contexts, counts, movements, and backups.

More detail:

- [Developer context](docs/DEV_CONTEXT.md)
- [Data flow](docs/dataflow.md)
- [Configuration and deployment](docs/configuration.md)
- [Changelog](docs/CHANGELOG.md)

## Configuration

`config.py` is tracked and should contain structure plus safe defaults only. Real
secrets must come from environment variables, local ignored files, or the
temporary PyInstaller bundled config workflow.

Configuration priority:

1. Real environment variables
2. `KASSENSTURZ_ENV_FILE`, source/dev runs only
3. `kassensturz.env`, source/dev runs only
4. `.env`, source/dev runs only
5. Bundled PyInstaller config from `kassensturz_secrets.py`, frozen builds only
6. Safe defaults from `config.py`

For local development, copy `.env.example` to `kassensturz.env` and fill in the
real values.

For Docker, inject the same `KASSENSTURZ_*` values through the container
environment or the server platform's secret management.

For the temporary PyInstaller build, generate an ignored bundled config module
before building. This lets the portable app run without a visible config file:

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

Create local configuration:

```powershell
Copy-Item .env.example kassensturz.env
```

Run the app:

```powershell
.\venv\Scripts\python.exe app.py
```

By default, development data is stored under `data/debug/`.

## Tests

Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m pytest tests
```

The suite covers storage behavior, service workflows, route wiring, export/import
roundtrips, config loading, and bundled PyInstaller config generation.

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

Until then, the PyInstaller build can bundle a generated, ignored config module
so trusted users can run the app without handling credentials directly.

## License

MIT License. See [docs/LICENSE](docs/LICENSE).
