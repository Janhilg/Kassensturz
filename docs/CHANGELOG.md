# Changelog

All notable changes to this project will be documented in this file.

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
- Extended tests for object-oriented services, bound storage, config loading, and bundled config generation.

### Changed

- Flask routes now build request objects and call app-level service wrappers instead of passing path/config keyword arguments through each route.
- `CashService` now owns a `CashSyncContext` and returns typed result objects, while compatibility wrappers still return dictionaries for older call sites.
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
