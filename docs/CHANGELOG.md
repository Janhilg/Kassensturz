# Changelog

All notable changes to this project will be documented in this file.

## [0.2.23] - 2026-05-04

### Added

- Added dedicated `CashSyncService` tests for direct sync pipeline and
  production bootstrap behavior, separate from `CashService` coverage.

## [0.2.22] - 2026-05-04

### Changed

- Refreshed import-path and development docs to state that `core.storage` is
  compatibility-only, not an active internal migration path.

## [0.2.21] - 2026-05-04

### Changed

- Removed the legacy `app.storage` export now that tests and internal scripts
  use direct storage imports instead.

## [0.2.20] - 2026-05-04

### Changed

- Split backup/export/import/upload orchestration from `CashService` into the
  dedicated `CashSyncService`.
- Kept `CashService` focused on cash count and cash movement business behavior,
  while preserving delegate methods for existing web-app call sites.

## [0.2.19] - 2026-05-04

### Added

- Added focused `CashServiceStorage` tests for bound storage repositories and
  unbound storage repositories that need `db_path` injection.

## [0.2.18] - 2026-05-04

### Changed

- Added a `CashServiceStorage` adapter so `CashService` can use explicit
  storage operations instead of string-based `_storage_call(...)` dispatch.
- Kept support for bound `CashStorage(db_path)` and unbound storage test
  doubles inside the adapter rather than in service workflow code.

## [0.2.17] - 2026-05-04

### Changed

- Updated service, export, and route tests to use focused storage modules
  instead of the `core.storage` compatibility facade.
- Added a test import-path guard so `core.storage` is only imported by explicit
  compatibility coverage.

## [0.2.16] - 2026-05-04

### Changed

- Removed the remaining internal `core.storage` compatibility imports from the
  app, web app, cash service, and `CashStorage` adapter.
- Tightened the implementation import-path guard so no `core.storage`
  compatibility imports are allowlisted anymore.

## [0.2.15] - 2026-05-04

### Fixed

- Overrode the test `tmp_path` fixture to create plain per-test directories
  without pytest's Windows-problematic `*current` symlinks.

## [0.2.14] - 2026-05-04

### Fixed

- Configured pytest to use a repo-local temp directory so Windows does not
  resolve pytest's `tmp_path` helper links under an untrusted user temp mount.
- Ignored local pytest and Ruff cache directories.

## [0.2.13] - 2026-05-04

### Changed

- Export utilities now import focused storage implementation modules directly
  instead of using the `core.storage` compatibility facade.
- Tightened the compatibility-import allowlist after moving exports off the
  storage facade.

## [0.2.12] - 2026-05-04

### Added

- Added an allowlist-based import-path test to prevent new compatibility facade
  imports from creeping into implementation files.

## [0.2.11] - 2026-05-04

### Changed

- Storage-focused tests and shared storage fixtures now import focused storage
  modules directly instead of using the `core.storage` compatibility facade.
- Added a regression test to keep storage-domain tests on direct storage
  imports, while preserving the small `core.storage` compatibility test.

## [0.2.10] - 2026-05-04

### Changed

- Storage repository classes now call the focused storage implementation modules
  directly instead of going through the `core.storage` compatibility facade.
- Added a regression test to keep repository classes off the storage facade.

## [0.2.9] - 2026-05-04

### Changed

- Split the large storage function module into focused implementation modules
  for connection helpers, migrations, accounts, contexts, counts, movements, and
  backups.
- Kept `core.storage` as a compatibility facade for older call sites.
- Added import-path documentation that points new code to direct implementation
  modules and classes.

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
