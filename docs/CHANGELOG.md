# Changelog

All notable changes to this project will be documented in this file.

---

## [0.2.0] - 2026-04-30

### ✨ Added

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

### 🔄 Changed

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

### 🐛 Fixed

- Multiple sync-related issues:
  - foreign key constraint failures
  - mismatched account IDs across devices
- Import issues with legacy Excel data
- Logging format errors (mismatched placeholders)
- Theme inconsistencies between light and dark mode
- Form styling inconsistencies (select / textarea)
- Navigation layout mismatch with content width
- Calculator/cash counter form integration issues

---

### 🧪 Tests

- Rebuilt test suite from scratch
- Added coverage for:
  - storage layer (accounts, counts, movements, contexts)
  - service layer (business logic + sync orchestration)
  - export/import roundtrip
  - Flask routes
- Added shared fixtures via `conftest.py`
- Introduced mock-based testing for sync behavior

---

### 🧠 Notes

- This is the first stable version of Kassensturz
- The system now uses a simple and explicit model:
  - **counts define reality**
  - **movements define flow**
- Sync is designed to be safe and append-only

---

## [Unreleased]

### Planned

- Discrepancy detection (expected vs counted balance)
- Improved analytics per context/event
- Sync diagnostics and visualization
- Mobile UX improvements