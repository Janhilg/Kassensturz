# Changelog

All notable changes to this project will be documented in this file.

## [0.2.8] - 2026-05-04

### Added

- Added a sanitized legacy Excel workbook fixture covering spreadsheet-specific
  date, time, currency, and status quirks.

### Changed

- Legacy cash-count import now handles Excel serial dates/times, German
  two-digit date text, dotted time text, non-breaking currency spaces, and
  common German status labels.

## [0.2.7] - 2026-05-04

### Changed

- Debug/source runs now read the ignored `kassensturz_secrets.py` fallback, so
  the local server and temporary PyInstaller build can share the same secrets
  module.
- Environment variables still take priority over the ignored secrets module for
  Docker/server deployment.

## [0.2.6] - 2026-05-04

### Added

- Added admin dashboard status for the production bootstrap import path.
- Bootstrap checks now record skipped/imported status, reason, timestamp, mode,
  and latest successful import metadata in sync state.

## [0.2.5] - 2026-05-04

### Changed

- Reworked the app/core file structure toward one Python file per class.
- Moved Flask app classes into `web/app_paths.py` and
  `web/kassensturz_web_app.py`, leaving `app.py` as the entrypoint.
- Moved cash workflow classes into `core/cash/`.
- Moved storage object/repository classes into `core/storage_objects/`.
- Kept compatibility modules such as `core.cash_service`, `core.storage`,
  `core.export_utils`, `core.nextcloud_sync`, and `core.sync_state`.

## [0.2.4] - 2026-05-04

### Added

- Added production-only remote bootstrap import for empty databases.
- Added legacy Excel import support for cash-count workbooks with columns:
  `Date`, `Timestamp`, `Event name`, `Counted by`, `Cash sum`, `Event status`,
  and `Comment`.
- Added tests for legacy workbook parsing and production bootstrap import.

## [0.2.3] - 2026-05-04

### Added

- Added `core/version.py` as the central source for app and database schema versions.
- Added SQLite schema versioning through `PRAGMA user_version`.
- Added a baseline schema migration/repair path for unversioned local databases.
- Added admin status metadata for app version and database schema version.
- Added migration tests for fresh databases, unversioned legacy databases, and newer unsupported schema versions.

### Changed

- Removed the old path-heavy cash service compatibility wrappers after moving routes and tests to request/context-based calls.
- `storage.ensure_db_file()` now runs the migration layer before storage operations continue.

## [0.2.2] - 2026-05-04

### Added

- Introduced `KassensturzWebApp`, `AppPaths`, `create_web_app()`, and `create_app()` for explicit app construction.
- Added request/result objects for cash workflows:
  - `CashCountRequest`
  - `CashMovementRequest`
  - `CashSyncContext`
  - `SyncResult`
- Added bound storage repositories through `CashStorage(db_path)`:
  - accounts
  - contexts
  - movements
  - counts
  - backups
- Added environment-based configuration with source/dev env-file loading.
- Added temporary PyInstaller bundled config support via ignored `kassensturz_secrets.py`.
- Added `tools/create_bundled_config.py` to generate bundled config from a local env file.
- Added Ruff configuration in `pyproject.toml`.
- Added `requirements-dev.txt` for pytest, Ruff, and PyInstaller tooling.
- Added `tools/check.ps1` to run tests, linting, and format checks locally.
- Added Docker draft setup with `Dockerfile`, tracked `.dockerignore`, `docker-compose.yml`, and `docker.env.example`.
- Extended tests for object-oriented services, bound storage, config loading, and secrets-module generation.

### Changed

- Flask routes now build request objects and call app-level service methods instead of passing path/config keyword arguments through each route.
- `CashService` now owns a `CashSyncContext` and returns typed result objects.
- `config.py` is tracked again and contains only structure plus safe defaults.
- Docker/server deployments are documented as environment-driven, while PyInstaller is documented as a trusted-user portable workaround.

### Security

- Removed hard-coded Nextcloud and Flask secrets from tracked config.
- Added `.env.example` for local setup without committing real values.
- Added `kassensturz_secrets.py` to `.gitignore`.

## [0.2.1] - 2026-04-30


### Added
- Automation/Business logic
When you record a movement:

Runner Float → Supplier / Drinks Purchase

the service will:

save the supplier purchase movement
update balances
check the remaining balance of Runner Float
if there is money left, automatically create:
Runner Float → Bar Cash Box

for the remaining amount

That resets the runner float back to zero.

### Changed

- Cash counter UX improvements

---

## [0.2.0] - 2026-04-30

### Added

- Local-first cash tracking model
- Cash count functionality with:
  - denomination support (bills, coins, rolls)
  - free-text context
- Cash movement tracking between accounts
- Live balance tracking per cash account
- Shared calculator + cash counter component
- Cash counter:
  - bills, coins, and roll support
  - apply-to-form integration
- Balances page:
  - current balances
  - recent counts and movements
- Admin page:
  - sync trigger
  - export rebuild
  - backup restore
  - sync state display
- SQLite backup system with rotation
- Excel (`.xlsx`) and text (`.txt`) export
- Optional Nextcloud sync via WebDAV
- English / German language switching
- Dark / Light theme support
- Modular frontend structure (base template, shared components)

---

### Changed

- Refactored data model:
  - replaced old `entries` system with:
    - `cash_accounts`
    - `cash_counts`
    - `cash_movements`
    - `cash_contexts`
- Introduced **fixed account IDs** for reliable multi-device sync
- Reworked business logic:
  - cash counts now set account balances
  - movements adjust balances incrementally
- Removed `movement_type`:
  - movement meaning now derived from accounts
- Simplified sync model:
  - append-only merge
  - no overwrites
- Improved UI layout:
  - centered two-column layout
  - consistent navigation bar
  - shared base template
- Extracted reusable calculator/cash-counter component
- Improved context handling:
  - auto-prefill with latest context
  - free-text input with suggestions
- Refactored logging:
  - structured logs for storage, service, and sync
- Reorganized CSS:
  - split into base / layout / form / theme / admin / calculator
  - removed duplicate and conflicting styles
- Reworked tests:
  - new pytest suite aligned with refactored architecture
  - added fixtures and service-level testing

---

### Tests

- Rebuilt test suite from scratch
- Added coverage for:
  - storage layer (accounts, counts, movements, contexts)
  - service layer (business logic + sync orchestration)
  - export/import roundtrip
  - Flask routes
- Added shared fixtures via `conftest.py`
- Introduced mock-based testing for sync behavior

---

### Notes

- This is the first stable version of Kassensturz
- The system now uses a simple and explicit model:
  - **counts define reality**
  - **movements define flow**
- Sync is designed to be safe and append-only
