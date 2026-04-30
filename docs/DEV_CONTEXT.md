# 🧠 Kassensturz – Project Context for Development

This document provides context for working on the Kassensturz project in a new chat or development session.

It is not user documentation — it is meant for developers / AI assistants.

---

## 🎯 Purpose of the Project

Kassensturz is a local-first cash tracking system built with Flask.

It tracks:
- physical cash counts (ground truth)
- cash movements (money flow)
- current balances per cash box

---

## 🧠 Core Business Logic

### Balance model (IMPORTANT)

- Cash count = authoritative truth
- Movement = delta applied to balance

Example:

Bar Cash Box = 200€
Bar → Runner (50€)

→ Bar = 150€
→ Runner = 50€

Balances are stored in:
cash_accounts.current_balance_cents

---

## 🧱 Architecture

### Local-first

- SQLite DB = single source of truth
- Excel/TXT = exports only
- Nextcloud = sync transport

---

## 📦 Key Modules

core/
  storage.py
  cash_service.py
  export_utils.py
  nextcloud_sync.py
  sync_state.py

app.py

---

## 🗄️ Data Model

- cash_accounts → cash boxes + balance
- cash_counts → physical counts
- cash_movements → money flow
- cash_contexts → grouping

---

## ⚠️ Important Design Decisions

- No movement_type (derived from accounts)
- Fixed account IDs across devices
- current_balance_cents is local state
- Sync is append-only

---

## 🔄 Sync Flow

1. Export local DB
2. Download remote Excel
3. Import & merge
4. Re-export
5. Upload
6. Save sync state

---

## ⚠️ Known Pitfalls

- Foreign key errors due to mismatched account IDs
- Schema changes require DB reset

---

## 🧮 Frontend

- Vanilla JS
- Modular CSS
- Shared base layout
- Calculator partial reused across pages

---

## 🔐 Admin Features

- Sync
- Rebuild exports
- Restore backups
- View sync state

---

## 🧠 Summary

Kassensturz is:
- local-first
- simple
- explicit
- append-only

Avoid hidden logic and over-complication.
