# Kassensturz Development Context

This file is a handoff note for developers and AI assistants. It describes the
current shape of the project, the decisions that should stay stable, and the
places where future changes are most likely to fit.

## Product Purpose

Kassensturz is a local-first cash tracking app for small event or venue cash
operations.

It records:

- physical cash counts
- cash movements between accounts
- live balances per account
- exports and optional Nextcloud sync state

The app should stay simple, explicit, and reliable. Avoid clever hidden behavior
around money movement.

## Domain Rules

Cash counts define reality. Cash movements define flow.

```text
Count:    Bar Cash Box = 200.00 EUR
Movement: Bar Cash Box -> Runner Float = 50.00 EUR

Result:   Bar Cash Box = 150.00 EUR
          Runner Float = 50.00 EUR
```

Important rules:

- `cash_accounts.current_balance_cents` stores the live balance.
- A count sets an account balance to the counted total.
- A movement subtracts from the source account and adds to the target account.
- A movement must have at least a source or a target account.
- A movement cannot use the same account as both source and target.
- Fixed account IDs must remain stable for multi-device sync.
- Account names shown in the UI should be translated through stable IDs/i18n keys.

Special current rule:

- A movement from `Runner Float` to `Supplier / Drinks Purchase` automatically
  returns remaining runner float balance to `Bar Cash Box`.

## Architecture Overview

The application is object-oriented at the app, service, and storage boundaries.

```text
app.py
  AppPaths
  KassensturzWebApp
  create_web_app()
  create_app()

core/
  cash_service.py
  storage.py
  export_utils.py
  nextcloud_sync.py
  sync_state.py
  admin_service.py
  service.py
```

`core/service.py` is a legacy guard module. It exists to fail loudly if older
entry-based sync code is called.

## App Layer

`KassensturzWebApp` owns:

- Flask app construction
- route registration
- template context helpers
- path configuration through `AppPaths`
- service wiring
- app-level wrapper methods used by tests

Routes should build request objects and call app-level wrappers:

- `record_cash_count(CashCountRequest)`
- `record_cash_movement(CashMovementRequest)`
- `rebuild_exports()`

The older compatibility methods still exist because some code and tests exercise
them:

- `record_cash_count_and_sync(...)`
- `record_cash_movement_and_sync(...)`
- `rebuild_exports_and_sync(...)`

When adding or changing routes, prefer testing against the app-level wrapper
methods. That keeps route tests focused on request parsing and response behavior.

## Service Layer

`CashService` owns business workflows and the full sync pipeline.

Main data objects in `core/cash_service.py`:

- `CashSyncContext`
- `CashCountRequest`
- `CashMovementRequest`
- `SyncResult`
- `CashCountResult`
- `CashMovementResult`

`CashSyncContext` carries runtime infrastructure:

- SQLite DB path
- Excel export path
- text export path
- backup directory
- sync state file
- config object

New application code should call:

- `CashService.record_count(request)`
- `CashService.record_movement(request)`
- `CashService.rebuild_exports()`

Compatibility wrappers return dictionaries for older call sites. The typed result
objects expose `to_dict()` for route flash messages and compatibility tests.

## Storage Layer

`core/storage.py` contains two APIs:

- module-level functions kept for compatibility and focused tests
- bound object/repository API for new object-oriented usage

Prefer this style in new code:

```python
storage = CashStorage(db_path)
storage.ensure_db_file()
storage.accounts.seed_defaults()

account = storage.accounts.by_name("Bar Cash Box")
storage.counts.create(
    cash_account_id=account["id"],
    counted_by="Jan",
    total_cents=12345,
    count_type="opening",
)
```

Bound repositories:

- `CashAccountRepository`
- `CashContextRepository`
- `CashMovementRepository`
- `CashCountRepository`
- `CashBackupRepository`

Do not remove the module-level functions casually. They are still useful for
tests and for preserving older call sites while the refactor settles.

## Export and Sync

The local SQLite DB is the source of truth. Excel and text files are derived
exports.

Sync pipeline:

1. Create a database backup.
2. Export local DB to Excel and text.
3. Download remote Excel if Nextcloud is configured and the remote file exists.
4. Import remote workbook data.
5. Merge accounts, contexts, counts, and movements append-only.
6. Re-export the full dataset.
7. Upload Excel and text exports.
8. Write sync state.

Responsibilities:

- `CashService`: workflow orchestration and business rules
- `CashExportService`: Excel/text import and export
- `NextcloudClient`: WebDAV transport only
- `SyncStateStore`: sync metadata persistence

Do not put business rules in `nextcloud_sync.py`.

## Data Model

Tables:

- `cash_accounts`: stable accounts and live balance
- `cash_contexts`: reusable/free-text event labels
- `cash_counts`: physical count records
- `cash_movements`: money flow records

Design decisions:

- no `movement_type`; meaning is derived from accounts
- sync imports are append-only
- stable IDs are more important than display names
- exports are replaceable artifacts
- local backups are created before sync/export work

## Configuration and Secrets

`config.py` is tracked. It must contain structure and safe defaults only.

Runtime configuration priority:

1. real environment variables
2. `KASSENSTURZ_ENV_FILE`, source/dev only
3. `kassensturz.env`, source/dev only
4. `.env`, source/dev only
5. bundled PyInstaller config from `kassensturz_secrets.py`, frozen builds only
6. safe defaults from `config.py`

Never commit:

- `kassensturz.env`
- `.env`
- `kassensturz_secrets.py`
- real Nextcloud credentials
- real Flask or admin secrets

For source development, use `kassensturz.env`.

For the temporary PyInstaller build, generate an ignored bundled config module:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

This hides secrets from casual viewing and keeps them out of Git. It is practical
obscurity for trusted users, not a security boundary against reverse engineering.

For the intended Docker/server deployment, inject secrets through environment
variables or the server platform's secret management.

Full details live in [configuration.md](configuration.md).

## Frontend Notes

The frontend is server-rendered HTML with vanilla JavaScript.

Current UI pieces:

- shared base template
- cash count page
- cash movement page
- balances page
- admin page
- shared calculator/cash-counter partial
- English/German translations
- dark/light theme

When changing account labels, keep the translation-key behavior in mind:

- default accounts use stable IDs such as `acc_bar_cash_box`
- templates should use generated `account_*` i18n keys
- visible account names should not be the only translation source

## Tests

Install dev dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m pytest tests
```

Run lint and format checks:

```powershell
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m ruff format --check .
```

Run everything locally:

```powershell
.\tools\check.ps1
```

Current coverage focus:

- storage functions
- bound storage repositories
- service request/result workflows
- sync pipeline dependency ordering
- Flask route parsing and wrapper calls
- export/import roundtrip
- config loading
- bundled PyInstaller config generation
- legacy guard behavior

Tooling files:

- `requirements.txt`: runtime dependencies
- `requirements-dev.txt`: runtime plus pytest, Ruff, and PyInstaller
- `pyproject.toml`: Ruff lint/format configuration
- `tools/check.ps1`: local test/lint/format check script

## Common Change Patterns

For a new cash workflow:

1. Add or extend a request dataclass in `cash_service.py`.
2. Implement validation and business behavior in `CashService`.
3. Use bound storage repositories where possible.
4. Add app-level wrapper methods if routes need to call it.
5. Test service behavior with fake dependencies.
6. Test route parsing separately from service internals.

For a storage change:

1. Keep module-level functions working.
2. Add or update the relevant bound repository method.
3. Cover both persistence behavior and any merge/import edge cases.

For config changes:

1. Keep `config.py` safe to commit.
2. Update `.env.example`.
3. Update `docs/configuration.md`.
4. Add or update tests in `tests/test_config_env.py`.

## Known Pitfalls

- Foreign key errors usually mean account IDs changed or remote data references
  accounts that do not exist locally.
- Schema changes need a migration plan or a deliberate dev DB reset.
- Do not reintroduce secrets into `config.py`.
- Do not make the PyInstaller bundled config sound cryptographically secure.
- Do not move route parsing assertions into service tests; keep layers separate.
- Preserve compatibility wrappers until all old call sites are intentionally gone.

## Useful Docs

- [Data flow](dataflow.md)
- [Configuration and deployment](configuration.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)
