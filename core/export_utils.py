import hashlib
from pathlib import Path

from openpyxl import Workbook, load_workbook

from core.storage import DENOM_FIELDS, fetch_all_entries

EXCEL_HEADERS = [
    "ID",
    "Date",
    "Timestamp",
    "Event name",
    "Counted by",
    "Cash sum",
    "Event status",
    "Comment",
    "100 €",
    "50 €",
    "20 €",
    "10 €",
    "5 €",
    "2 €",
    "1 €",
    "0.50 €",
    "0.20 €",
    "0.10 €",
]

EXCEL_TO_DB_MAP = {
    "ID": "id",
    "Date": "date",
    "Timestamp": "timestamp",
    "Event name": "event_name",
    "Counted by": "counted_by",
    "Cash sum": "cash_sum",
    "Event status": "event_status",
    "Comment": "comment",
    "100 €": "denom_100",
    "50 €": "denom_50",
    "20 €": "denom_20",
    "10 €": "denom_10",
    "5 €": "denom_5",
    "2 €": "denom_2",
    "1 €": "denom_1",
    "0.50 €": "denom_050",
    "0.20 €": "denom_020",
    "0.10 €": "denom_010",
}

LEGACY_HEADER_WITH_COUNTER = [
    "Date",
    "Timestamp",
    "Event name",
    "Counted by",
    "Cash sum",
    "Event status",
    "Comment",
]

LEGACY_HEADER_NO_COUNTER = [
    "Date",
    "Timestamp",
    "Event name",
    "Cash sum",
    "Event status",
    "Comment",
]


def excel_safe_value(value):
    return "" if value is None else value


def shorten_id(value):
    if value is None:
        return ""
    return str(value)[:12]


def legacy_row_id(values: list) -> str:
    normalized = "|".join("" if value is None else str(value) for value in values)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def entry_to_excel_row(entry: dict, shorten_ids: bool = False) -> list:
    entry_id = entry.get("id")
    if shorten_ids:
        entry_id = shorten_id(entry_id)

    return [
        excel_safe_value(entry_id),
        excel_safe_value(entry.get("date")),
        excel_safe_value(entry.get("timestamp")),
        excel_safe_value(entry.get("event_name")),
        excel_safe_value(entry.get("counted_by")),
        excel_safe_value(entry.get("cash_sum")),
        excel_safe_value(entry.get("event_status")),
        excel_safe_value(entry.get("comment")),
        excel_safe_value(entry.get("denom_100")),
        excel_safe_value(entry.get("denom_50")),
        excel_safe_value(entry.get("denom_20")),
        excel_safe_value(entry.get("denom_10")),
        excel_safe_value(entry.get("denom_5")),
        excel_safe_value(entry.get("denom_2")),
        excel_safe_value(entry.get("denom_1")),
        excel_safe_value(entry.get("denom_050")),
        excel_safe_value(entry.get("denom_020")),
        excel_safe_value(entry.get("denom_010")),
    ]


def export_entries_to_excel(db_path: Path, file_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Kassensturz"
    sheet.append(EXCEL_HEADERS)

    for entry in fetch_all_entries(db_path):
        sheet.append(entry_to_excel_row(entry))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(file_path)


def format_ascii_table(headers, rows):
    string_rows = [
        ["" if value is None else str(value) for value in row]
        for row in rows
    ]

    widths = [len(str(header)) for header in headers]
    for row in string_rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def make_separator():
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def make_row(values):
        padded = [f" {str(value).ljust(widths[idx])} " for idx, value in enumerate(values)]
        return "|" + "|".join(padded) + "|"

    lines = [make_separator(), make_row(headers), make_separator()]
    for row in string_rows:
        lines.append(make_row(row))

    return "\n".join(lines)


def export_entries_to_text(db_path: Path, file_path: Path):
    rows = [entry_to_excel_row(entry, shorten_ids=True) for entry in fetch_all_entries(db_path)]
    content = format_ascii_table(EXCEL_HEADERS, rows)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def get_cell_value(row, index_map, column_name, default=""):
    idx = index_map.get(column_name)
    if idx is None or idx >= len(row):
        return default
    value = row[idx]
    return default if value is None else value


def map_excel_row_to_entry(row, index_map) -> dict:
    return {
        db_key: get_cell_value(row, index_map, excel_key, None if db_key in DENOM_FIELDS else "")
        for excel_key, db_key in EXCEL_TO_DB_MAP.items()
    }


def import_entries_from_excel(file_path: Path) -> list[dict]:
    workbook = load_workbook(file_path, data_only=True)
    sheet = workbook.active

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    index_map = {name: idx for idx, name in enumerate(header)}
    imported_entries = []

    for raw_row in rows[1:]:
        row = list(raw_row)

        if "ID" in index_map:
            entry = map_excel_row_to_entry(row, index_map)
            entry_id = str(entry.get("id", "")).strip()
            if entry_id:
                imported_entries.append(entry)
            continue

        if all(col in index_map for col in LEGACY_HEADER_WITH_COUNTER):
            legacy_values = [
                get_cell_value(row, index_map, "Date", ""),
                get_cell_value(row, index_map, "Timestamp", ""),
                get_cell_value(row, index_map, "Event name", ""),
                get_cell_value(row, index_map, "Counted by", ""),
                get_cell_value(row, index_map, "Cash sum", ""),
                get_cell_value(row, index_map, "Event status", ""),
                get_cell_value(row, index_map, "Comment", ""),
                get_cell_value(row, index_map, "100 €", ""),
                get_cell_value(row, index_map, "50 €", ""),
                get_cell_value(row, index_map, "20 €", ""),
                get_cell_value(row, index_map, "10 €", ""),
                get_cell_value(row, index_map, "5 €", ""),
                get_cell_value(row, index_map, "2 €", ""),
                get_cell_value(row, index_map, "1 €", ""),
                get_cell_value(row, index_map, "0.50 €", ""),
                get_cell_value(row, index_map, "0.20 €", ""),
                get_cell_value(row, index_map, "0.10 €", ""),
            ]

            imported_entries.append({
                "id": legacy_row_id(legacy_values),
                "date": legacy_values[0],
                "timestamp": legacy_values[1],
                "event_name": legacy_values[2],
                "counted_by": legacy_values[3],
                "cash_sum": legacy_values[4],
                "event_status": legacy_values[5],
                "comment": legacy_values[6],
                "denom_100": legacy_values[7] or None,
                "denom_50": legacy_values[8] or None,
                "denom_20": legacy_values[9] or None,
                "denom_10": legacy_values[10] or None,
                "denom_5": legacy_values[11] or None,
                "denom_2": legacy_values[12] or None,
                "denom_1": legacy_values[13] or None,
                "denom_050": legacy_values[14] or None,
                "denom_020": legacy_values[15] or None,
                "denom_010": legacy_values[16] or None,
            })
            continue

        if all(col in index_map for col in LEGACY_HEADER_NO_COUNTER):
            legacy_values = [
                get_cell_value(row, index_map, "Date", ""),
                get_cell_value(row, index_map, "Timestamp", ""),
                get_cell_value(row, index_map, "Event name", ""),
                "",
                get_cell_value(row, index_map, "Cash sum", ""),
                get_cell_value(row, index_map, "Event status", ""),
                get_cell_value(row, index_map, "Comment", ""),
                get_cell_value(row, index_map, "100 €", ""),
                get_cell_value(row, index_map, "50 €", ""),
                get_cell_value(row, index_map, "20 €", ""),
                get_cell_value(row, index_map, "10 €", ""),
                get_cell_value(row, index_map, "5 €", ""),
                get_cell_value(row, index_map, "2 €", ""),
                get_cell_value(row, index_map, "1 €", ""),
                get_cell_value(row, index_map, "0.50 €", ""),
                get_cell_value(row, index_map, "0.20 €", ""),
                get_cell_value(row, index_map, "0.10 €", ""),
            ]

            imported_entries.append({
                "id": legacy_row_id(legacy_values),
                "date": legacy_values[0],
                "timestamp": legacy_values[1],
                "event_name": legacy_values[2],
                "counted_by": legacy_values[3],
                "cash_sum": legacy_values[4],
                "event_status": legacy_values[5],
                "comment": legacy_values[6],
                "denom_100": legacy_values[7] or None,
                "denom_50": legacy_values[8] or None,
                "denom_20": legacy_values[9] or None,
                "denom_10": legacy_values[10] or None,
                "denom_5": legacy_values[11] or None,
                "denom_2": legacy_values[12] or None,
                "denom_1": legacy_values[13] or None,
                "denom_050": legacy_values[14] or None,
                "denom_020": legacy_values[15] or None,
                "denom_010": legacy_values[16] or None,
            })

    return imported_entries