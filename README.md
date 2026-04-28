# Kassensturz

Kassensturz is a small Flask web application for recording cash events.

It provides:
- A web Interface to save cash box sum with essetial data, e.g. date, name and start or stop
- a live calculator / cash counter
- Local Excel export using `.xlsx` and `.txt`
- Local data backup, SQLite
- optional upload of the Excel and `.txt` file to Nextcloud via WebDAV
- DB/Excel file merging to sync information. Remote as append only.
- English/German language switching
- Dark / Light mode

![Screenshot1 of Kassenstutz Webapp](/assets/Screenshot%202026-04-28%20100743.png)

![Screenshot1 of Kassenstutz Webapp](/assets/Screenshot%202026-04-28%20100819.png)

## Build (recommended: portable folder / onedir)

This creates a **portable folder** containing the executable and all required files.

### Windows

```bash
pyinstaller --onedir --name Kassensturz \
  --icon=assets/cash.ico \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --noconfirm \
  app.py
```

as one line:
```bash
pyinstaller --onedir --name Kassensturz  --icon=assets/cash.ico --add-data "templates:templates" --add-data "static:static" --noconfirm app.py
```

Output will be in:

```text
dist/Kassensturz/
```

You can copy this entire folder to another machine or USB stick and run:

```text
Kassensturz.exe
```

## Features

### Form
The form lets you submit:
- Date
- Event name
- Accountant Name
- Cash sum
- Event Start/Stop
- Comment (optional)
  
Optional:
- Cash denominations
Each confirmed submission is appended as a new row in the Excel file.

### Live calculator and cash counter
Live calculator on page to sum up cash

Cash denomination counter

### Nextcloud upload
After each successful submission, the Excel file is be merged with and uploaded to Nextcloud using WebDAV.




