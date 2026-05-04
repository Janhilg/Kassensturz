# Kassensturz Development Context

This document is for developers and AI assistants working on the project.

## Purpose

Kassensturz is a local-first cash tracking system built with Flask.

It tracks:

- physical cash counts as ground truth
- cash movements as money flow
- current balances per cash account
- local exports and optional Nextcloud sync

## Core Business Logic

Cash counts set reality. Cash movements apply deltas.

Example:

```text
Bar Cash Box = 200 EUR
Bar Cash Box -> Runner Float = 50 EUR

Bar Cash Box = 150 EUR
Runner Float = 50 EUR
```

The current live balance is stored in `cash_accounts.current_balance_cents`.

## Architecture

The current app is object-oriented at the application and service boundaries.

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
```

### App Layer

`KassensturzWebApp` owns Flask route registration, path setup, service wiring, and app-level helpers.

The route handlers build request objects:

- `CashCountRequest`
- `CashMovementRequest`

They call:

- `record_cash_count()`
- `record_cash_movement()`
- `rebuild_exports()`

Compatibility wrappers still exist for older call sites:

- `record_cash_count_and_sync()`
- `record_cash_movement_and_sync()`
- `rebuild_exports_and_sync()`

### Service Layer

`CashService` owns business rules and the sync pipeline.

Important service data objects:

- `CashSyncContext`
- `CashCountRequest`
- `CashMovementRequest`
- `SyncResult`
- `CashCountResult`
- `CashMovementResult`

`CashSyncContext` carries:

- SQLite database path
- Excel export path
- text export path
- backup directory
- sync state file
- runtime config

### Storage Layer

`core/storage.py` still exposes module-level functions for compatibility and focused tests.

New object-oriented usage should prefer:

```python
storage = CashStorage(db_path)
storage.ensure_db_file()
storage.accounts.seed_defaults()
storage.accounts.by_name("Bar Cash Box")
storage.counts.create(...)
storage.movements.create(...)
```

Bound repositories:

- `CashAccountRepository`
- `CashContextRepository`
- `CashMovementRepository`
- `CashCountRepository`
- `CashBackupRepository`

### Export and Sync

`CashExportService` exports and imports Excel/TXT data.

`NextcloudClient` is transport only. It should not own business logic.

`SyncStateStore` reads and writes sync metadata.

## Data Model

- `cash_accounts`: cash boxes, floats, sinks, bank, live balance
- `cash_counts`: physical cash counts
- `cash_movements`: money flow between accounts
- `cash_contexts`: free-text grouping labels

Important design decisions:

- fixed account IDs are required for multi-device sync
- account display labels are translated from stable IDs/i18n keys
- no `movement_type`; movement meaning is derived from source and target accounts
- sync import is append-only
- exports are derived artifacts, not source of truth

## Configuration

`config.py` is tracked and must contain structure only, not real secrets.

Runtime configuration priority:

1. real environment variables
2. `KASSENSTURZ_ENV_FILE`, source/dev only
3. `kassensturz.env`, source/dev only
4. `.env`, source/dev only
5. bundled PyInstaller config from `kassensturz_secrets.py`, frozen builds only
6. safe defaults from `config.py`

For Docker, inject `KASSENSTURZ_*` values through the container environment or secret management.

For the temporary PyInstaller build, generate an ignored bundled config module:

```powershell
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

This avoids shipping a visible config file with the portable app. It is practical obscurity for trusted users, not cryptographic protection.

Never commit:

- `kassensturz.env`
- `.env`
- `kassensturz_secrets.py`
- real Nextcloud credentials
- real Flask/admin secrets

## Sync Flow

1. Create a database backup.
2. Export local DB to Excel and text.
3. Download remote Excel if configured and present.
4. Import remote data.
5. Merge accounts, contexts, counts, and movements append-only.
6. Re-export the full dataset.
7. Upload Excel and text exports.
8. Save sync state.

## Tests

Run the full suite:

```powershell
.\venv\Scripts\python.exe -m pytest tests
```

Current test focus:

- storage functions and bound repositories
- service request/result objects
- sync pipeline behavior with fake dependencies
- Flask route wiring
- config loading and bundled config generation
- export/import roundtrip

## Known Pitfalls

- Foreign key errors usually mean account IDs were changed or remote data references accounts that do not exist locally.
- Schema changes may require a DB migration or a local dev DB reset.
- Do not move business logic into `nextcloud_sync.py`; keep it in `CashService`.
- Do not add new secrets to tracked files.
- When changing routes, keep tests patched against app-level wrapper methods rather than lower-level service internals.

## Summary

Kassensturz should stay:

- local-first
- explicit
- append-only for sync imports
- object-oriented at app/service/storage boundaries
- conservative about secrets in Git and portable builds
