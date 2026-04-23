# Kassensturz

Kassensturz is a small Flask web application for recording cash events.

It provides:
- save cash box sum with date and event
- a live calculator with add/subtract functionality
- Local Excel export using `.xlsx`
- optional upload of the Excel file to Nextcloud via WebDAV
- English/German language switching 

![Screenshot of Kassenstutz Webapp](/docu/Screenshot%202026-04-23.png)
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

## Project structure

```text
Kassensturz/
├── app.py
├── config.py
├── config.example.py
├── requirements.txt
├── README.md
├── docker-compose.yml
├── .gitignore
├── static/
│   └── style.css
└── templates/
    └── index.html

