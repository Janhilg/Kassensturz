# Kassensturz

Kassensturz is a small Flask web application for recording cash events.

It provides:
- save cash box sum with date and event
- a live calculator with add/subtract functionality
- Local Excel export using `.xlsx`
- optional upload of the Excel file to Nextcloud via WebDAV
- English/German language switching 

![Screenshot of Kassenstutz Webapp](/docu/Screenshot%202026-04-23.png)

## Build (recommended: portable folder / onedir)

This creates a **portable folder** containing the executable and all required files.

### Windows

```bash
pyinstaller --onedir --name Kassensturz ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  app.py
```

### Linux / macOS

```bash
pyinstaller --onedir --name Kassensturz \
  --add-data "templates:templates" \
  --add-data "static:static" \
  app.py
```

Output will be in:

```text
dist/Kassensturz/
```

You can copy this entire folder to another machine or USB stick and run:

```text
Kassensturz.exe   (Windows)
./Kassensturz     (Linux/macOS)
```

## Features

### Form
The form lets you submit:
- Date
- Event name
- Cash sum
- Comment (optional)

Each confirmed submission is appended as a new row in the Excel file.

### Live calculator
The calculator on the right side:
- adds or subtracts numbers without submitting the form
- updates instantly in the browser
- keeps a temporary session history
- can apply the current result to the `Cash sum` form field

### Excel storage
Submissions are stored in:

`kassensturz_data.xlsx`

### Nextcloud upload
After each successful submission, the Excel file can optionally be uploaded to Nextcloud using WebDAV.




