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
  create_web_app()
  create_app()

web/
  app_paths.py
  kassensturz_web_app.py

core/
  cash/
    cash_service.py
    cash_sync_service.py
    cash_service_storage.py
    cash_count_request.py
    cash_movement_request.py
    cash_sync_context.py
    result dataclasses
  storage_objects/
    cash_storage.py
    one repository class per file
  storage_accounts.py
  storage_contexts.py
  storage_counts.py
  storage_movements.py
  storage_migrations.py
  storage_connection.py
  storage_backups.py
  admin_maintenance_service.py
  cash_export_service.py
  nextcloud_client.py
  sync_state_store.py
  storage.py
  export_utils.py
  nextcloud_sync.py
  sync_state.py
  admin_service.py
  service.py
  version.py
```

`core/service.py` is a legacy guard module. It exists to fail loudly if older
entry-based sync code is called.

## App Layer

`web/kassensturz_web_app.py` owns `KassensturzWebApp`:

- Flask app construction
- route registration
- template context helpers
- path configuration through `AppPaths`
- service wiring
- thin app-level methods used by routes and route tests

Routes should build request objects and call app-level methods:

- `record_cash_count(CashCountRequest)`
- `record_cash_movement(CashMovementRequest)`
- `rebuild_exports()`

When adding or changing routes, prefer testing against the app-level
methods. That keeps route tests focused on request parsing and response behavior.

## Service Layer

`CashService` owns cash count and cash movement business behavior.
`CashSyncService` owns backup/export/import/upload orchestration and production
bootstrap imports.

Main data objects in `core/cash/`:

- `CashSyncContext`
- `CashCountRequest`
- `CashMovementRequest`
- `CashServiceStorage`
- `CashSyncService`
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
- `CashSyncService.rebuild_exports()`

The old path-heavy compatibility wrappers were removed. Typed result objects
expose `to_dict()` for route flash messages and any adapter-style test doubles.
`CashServiceStorage` is the adapter between `CashService` and storage
repositories; keep bound/unbound DB-path plumbing there instead of adding
string-based dispatch back into the service workflows.

## Storage Layer

Storage is split between function modules and one-class modules:

- `core/storage.py`: compatibility facade that re-exports old module-level
  SQLite function paths
- `core/storage_accounts.py`: account records, balances, and account statements
- `core/storage_contexts.py`: reusable/free-text context records
- `core/storage_counts.py`: cash count records and count imports
- `core/storage_movements.py`: cash movement records and movement imports
- `core/storage_migrations.py`: schema SQL, migrations, and DB initialization
- `core/storage_connection.py`: low-level connection and value helpers
- `core/storage_backups.py`: local backup create/list/restore helpers
- `core/storage_objects/`: bound object/repository API for new
  object-oriented usage, one class per file

New code should import direct modules and classes instead of reaching through
compatibility facades. For example, prefer
`from core.storage_objects.cash_storage import CashStorage` and
`from core.storage_counts import create_cash_count`. Existing
`from core import storage` call sites can move gradually. When touching tests or
internal code near a facade import, update only the imports in that local area;
do not turn a small change into a repo-wide import rewrite.

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

Do not remove facade exports casually. They are still useful for preserving
older call sites while the refactor settles.

## Versioning and Migrations

Application and database schema versions are centralized in `core/version.py`:

- `APP_VERSION`
- `DB_SCHEMA_VERSION`

SQLite uses `PRAGMA user_version` for database schema state. `storage.ensure_db_file()`
runs `migrate_database()` before normal storage operations continue.

Current schema version:

- `1`: baseline cash accounts, contexts, movements, counts, denominations, and
  append-only sync columns

Production bootstrap:

- When `Config.MODE == "production"` and the database has no counts or
  movements, startup attempts to download the configured remote Excel file.
- The importer accepts both the current Kassensturz multi-sheet workbook and the
  old production cash-count workbook.
- Legacy columns map as follows:
  `Event name` -> `context_label`, `Counted by` -> `counted_by`,
  `Cash sum` -> `total_cents`, `Event status` -> `count_type`,
  `Comment` -> `note`, and `Date`/`Timestamp` -> `counted_at`.
- Legacy rows are imported against `acc_bar_cash_box` because the old format had
  no account column.
- Legacy import IDs are deterministic, so re-importing the same remote rows does
  not create duplicates.
- A sanitized fixture workbook in `tests/fixtures/` covers legacy spreadsheet
  date, time, currency, and status quirks.
- Production bootstrap checks write `bootstrap_last_check` to sync state. A
  successful import also writes `bootstrap_last_import` and the legacy flat
  bootstrap counters for older diagnostics.
- The admin dashboard shows a dry-run status plus the latest recorded check and
  import metadata without contacting Nextcloud.

Migration rules:

- New DBs must end up at `DB_SCHEMA_VERSION`.
- Unversioned older DBs are treated as baseline candidates and repaired
  idempotently where possible.
- DBs with a schema version newer than the running app fail loudly.
- Future schema changes should add a new migration function, register it in
  `SCHEMA_MIGRATIONS`, increment `DB_SCHEMA_VERSION`, and add upgrade tests.

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
5. ignored secrets module from `kassensturz_secrets.py`, source/debug and frozen builds
6. safe defaults from `config.py`

Never commit:

- `kassensturz.env`
- `.env`
- `kassensturz_secrets.py`
- real Nextcloud credentials
- real Flask or admin secrets

For source development, use `kassensturz.env` or the ignored
`kassensturz_secrets.py` fallback. Real environment variables override both.

For the temporary PyInstaller build, generate an ignored secrets module:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

The same module is read by source/debug runs and included by `Kassensturz.spec`
when present. This hides secrets from casual viewing and keeps them out of Git.
It is practical obscurity for trusted users, not a security boundary against
reverse engineering.

For the intended Docker/server deployment, inject secrets through environment
variables or the server platform's secret management.

Docker draft files:

- `Dockerfile`: runtime image with Gunicorn
- `.dockerignore`: excludes local data, build outputs, caches, and secrets
- `docker-compose.yml`: local container run with named volumes
- `docker.env.example`: placeholder env file to copy to ignored `docker.env`

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
- secrets-module generation
- legacy guard behavior

Tooling files:

- `requirements.txt`: runtime dependencies
- `requirements-dev.txt`: runtime plus pytest, Ruff, and PyInstaller
- `pyproject.toml`: Ruff lint/format configuration
- `tools/check.ps1`: local test/lint/format check script

## Common Change Patterns

For a new cash workflow:

1. Add or extend a request dataclass in `core/cash/`.
2. Implement validation and business behavior in `core/cash/cash_service.py`.
3. Use bound storage repositories where possible.
4. Add app-level methods if routes need to call it.
5. Test service behavior with fake dependencies.
6. Test route parsing separately from service internals.

For a storage change:

1. Put new function behavior in the focused `core/storage_*.py` module.
2. Add or update the relevant bound repository method.
3. Re-export through `core/storage.py` only when older call sites still need it.
4. Cover both persistence behavior and any merge/import edge cases.

For a schema change:

1. Increment `DB_SCHEMA_VERSION` in `core/version.py`.
2. Add a migration function in `core/storage_migrations.py`.
3. Register the migration in `SCHEMA_MIGRATIONS`.
4. Update `CASH_*_COLUMNS` or repository methods if the public data shape changes.
5. Add tests for fresh DB creation and upgrade from the previous schema.

For config changes:

1. Keep `config.py` safe to commit.
2. Update `.env.example`.
3. Update `docs/configuration.md`.
4. Add or update tests in `tests/test_config_env.py`.

## Known Pitfalls

- Foreign key errors usually mean account IDs changed or remote data references
  accounts that do not exist locally.
- Schema changes need a registered migration and upgrade tests.
- Do not reintroduce secrets into `config.py`.
- Do not make the PyInstaller secrets-module workflow sound cryptographically secure.
- Do not move route parsing assertions into service tests; keep layers separate.
- Do not reintroduce path-heavy service wrappers; pass request objects and a
  `CashSyncContext` instead.

## Useful Docs

- [Data flow](dataflow.md)
- [Import paths](import_paths.md)
- [Configuration and deployment](configuration.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)
