# Kassensturz
![Version](https://img.shields.io/badge/version-v0.2.2-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Kassensturz is a local-first Flask web application for managing cash balances across multiple cash boxes.

It is designed for simple, reliable tracking of:
- cash counts (physical reality)
- cash movements (money flow)
- current balances per cash box

---

[Changelog](docs/CHANGELOG.md)

---

## 🧠 Core Concept

Kassensturz follows a simple model:

- **Cash count** → sets the current balance of a cash box  
- **Cash movement** → moves money between accounts and updates balances  

Count: Bar Cash Box = 200€
Movement: Bar → Runner (50€)
→ Bar = 150€, Runner = +50€

---

## 🔧 Features

### 💰 Cash Count (main page)
- Record cash counts per cash box
- Free-text context (e.g. event name)
- Optional denomination breakdown (bills, coins, rolls)
- Live calculator and cash counter integrated

---

### 🔄 Cash Movements
- Move cash between accounts (e.g. bar → entrance)
- Record payments (e.g. bar → supplier)
- Optional denomination tracking
- Shared cash counter for fast input

---

### 🧾 Balances Page
- Current balance per cash account
- Based on:
  - latest count (anchor)
  - movements (updates)
- Shows recent:
  - counts
  - movements

---

### ⚙️ Admin Page
- System status overview
- Manual sync trigger
- Rebuild exports
- Restore database backups
- Sync state visibility (import/upload info)

---

### 🧮 Live Calculator & Cash Counter
- Two modes:
  - Calculator (add/subtract)
  - Cash counter (denominations + rolls)
- Cash counter is default
- Supports:
  - bills
  - coins
  - roll values (e.g. 2€ roll = 50€)
- Can apply results directly to forms

---

### 💾 Storage & Backup
- SQLite database (local source of truth)
- Automatic rotating backups
- Manual restore via admin page

---

### 📤 Export & Sync
- Full export to:
  - Excel (.xlsx)
  - Text (.txt)
- Optional Nextcloud sync via WebDAV
- Append-only merge logic:
  - remote data is imported without overwriting
- Multi-device sync support

---

### 🌐 Localization & UI
- English / German language switching
- Dark / Light theme
- Consistent layout across all pages
- Mobile-friendly

---

## 📦 Architecture

### Local-first model
- SQLite database is the single source of truth
- Exports are generated from DB
- Sync merges remote data into local DB

### Data model
- cash_accounts → cash boxes + live balance
- cash_counts → physical counts
- cash_movements → money flow
- cash_contexts → grouping (free text)

---

## 🔄 Sync behavior

- Import remote Excel (if exists)
- Merge new rows (append-only)
- Rebuild full export
- Upload to Nextcloud
- Track sync state

---

## Configuration

Configuration is read in this order:

1. Real environment variables
2. `KASSENSTURZ_ENV_FILE`, if set, source/dev runs only
3. `kassensturz.env` in the project root, source/dev runs only
4. `.env` in the project root, source/dev runs only
5. Bundled PyInstaller config from `kassensturz_secrets.py`, frozen builds only
6. Safe defaults from `config.py`

For local development, copy `.env.example` to `kassensturz.env` and fill in the
real values.

For Docker, set the same `KASSENSTURZ_*` values through the container environment,
an `env_file`, or the server's secret management. Container environment variables
override any local env file.

For the temporary PyInstaller build, create an ignored bundled config module from
your local env file before building:

```
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

When `kassensturz_secrets.py` exists, `Kassensturz.spec` includes it in the app
bundle. The generated module is ignored by Git and stores values base64-encoded,
so the portable app works out of the box without shipping a visible config file.

Do not put real secrets in `config.py`, `.env.example`, `Kassensturz.spec`, or
any tracked file. Bundled PyInstaller config is practical obscurity for trusted
users, not a cryptographic security boundary. The Docker/server deployment should
still inject secrets through the environment or secret management.

---

## 🖥️ Build (portable / onedir)

### Windows

```
python tools/create_bundled_config.py kassensturz.env
pyinstaller Kassensturz.spec
```

Output:
```
dist/Kassensturz/
```
Run:

Kassensturz.exe

---


## 📄 License

MIT License

MIT License – free to use, modify and distribute.

Copyright (c) 2026
