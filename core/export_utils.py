import logging
from pathlib import Path

from openpyxl import Workbook, load_workbook

from core import storage

logger = logging.getLogger(__name__)


SHEET_CASH_ACCOUNTS = "CashAccounts"
SHEET_CASH_CONTEXTS = "CashContexts"
SHEET_CASH_MOVEMENTS = "CashMovements"
SHEET_CASH_COUNTS = "CashCounts"
SHEET_CASH_BALANCES = "CashBalances"


def _ensure_parent_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_sheet(ws, columns: list[str], rows: list[dict]):
    ws.append(columns)
    for row in rows:
        ws.append([row.get(column) for column in columns])


def _read_sheet_rows(workbook, sheet_name: str) -> list[dict]:
    if sheet_name not in workbook.sheetnames:
        return []

    ws = workbook[sheet_name]
    values = list(ws.values)
    if not values:
        return []

    header = list(values[0])
    rows = []

    for raw_row in values[1:]:
        if raw_row is None:
            continue

        row = dict(zip(header, raw_row))

        if all(value is None for value in row.values()):
            continue

        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = None
            else:
                cleaned[key] = value

        rows.append(cleaned)

    return rows


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _format_cents(cents) -> str:
    if cents is None:
        return ""
    return f"{int(cents) / 100:.2f}"


def export_excel(db_path: Path, excel_path: Path):
    storage.ensure_db_file(db_path)
    _ensure_parent_dir(excel_path)

    wb = Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)

    accounts = storage.fetch_all_cash_accounts(db_path, active_only=False)
    contexts = storage.fetch_recent_cash_contexts(db_path, limit=10000)
    movements = storage.fetch_all_cash_movements(db_path)
    counts = storage.fetch_all_cash_counts(db_path)
    balances = storage.fetch_cash_account_balances(db_path)

    ws_accounts = wb.create_sheet(SHEET_CASH_ACCOUNTS)
    _write_sheet(ws_accounts, storage.CASH_ACCOUNT_COLUMNS, accounts)

    ws_contexts = wb.create_sheet(SHEET_CASH_CONTEXTS)
    _write_sheet(ws_contexts, storage.CASH_CONTEXT_COLUMNS, contexts)

    movement_export_columns = [
        *storage.CASH_MOVEMENT_COLUMNS,
        "from_account_name",
        "to_account_name",
        "amount_eur",
    ]
    movement_export_rows = []
    for row in movements:
        movement_export_rows.append(
            {
                **row,
                "amount_eur": storage.cents_to_eur(int(row["amount_cents"])),
            }
        )

    ws_movements = wb.create_sheet(SHEET_CASH_MOVEMENTS)
    _write_sheet(ws_movements, movement_export_columns, movement_export_rows)

    count_export_columns = [
        *storage.CASH_COUNT_COLUMNS,
        "cash_account_name",
        "total_eur",
    ]
    count_export_rows = []
    for row in counts:
        count_export_rows.append(
            {
                **row,
                "total_eur": storage.cents_to_eur(int(row["total_cents"])),
            }
        )

    ws_counts = wb.create_sheet(SHEET_CASH_COUNTS)
    _write_sheet(ws_counts, count_export_columns, count_export_rows)

    balance_columns = [
        "id",
        "name",
        "account_type",
        "balance_cents",
        "balance_eur",
        "is_active",
        "sort_order",
    ]
    ws_balances = wb.create_sheet(SHEET_CASH_BALANCES)
    _write_sheet(ws_balances, balance_columns, balances)

    wb.save(excel_path)

    logger.info(
        "Excel export completed | path=%s accounts=%s contexts=%s movements=%s counts=%s",
        excel_path,
        len(accounts),
        len(contexts),
        len(movements),
        len(counts),
    )


def export_text(db_path: Path, text_path: Path):
    storage.ensure_db_file(db_path)
    _ensure_parent_dir(text_path)

    accounts = storage.fetch_all_cash_accounts(db_path, active_only=False)
    balances = storage.fetch_cash_account_balances(db_path)
    movements = storage.fetch_all_cash_movements(db_path)
    counts = storage.fetch_all_cash_counts(db_path)

    lines = []

    lines.append("=== CASH ACCOUNTS ===")
    for row in accounts:
        lines.append(
            " | ".join(
                [
                    _safe_str(row["name"]),
                    _safe_str(row["account_type"]),
                    f"active={row['is_active']}",
                    f"sort={row['sort_order']}",
                    _safe_str(row["id"]),
                ]
            )
        )

    lines.append("")
    lines.append("=== CASH BALANCES ===")
    for row in balances:
        lines.append(
            " | ".join(
                [
                    _safe_str(row["name"]),
                    _safe_str(row["account_type"]),
                    f"balance_eur={row['balance_eur']:.2f}",
                    f"balance_cents={row['balance_cents']}",
                ]
            )
        )

    lines.append("")
    lines.append("=== CASH MOVEMENTS ===")
    for row in movements:
        denom_summary = []
        for field in storage.DENOM_FIELDS:
            value = row.get(field)
            if value not in (None, "", 0):
                denom_summary.append(f"{field}={value}")

        lines.append(
            " | ".join(
                [
                    _safe_str(row["effective_at"]),
                    f"amount_eur={_format_cents(row['amount_cents'])}",
                    f"from={_safe_str(row.get('from_account_name'))}",
                    f"to={_safe_str(row.get('to_account_name'))}",
                    f"context={_safe_str(row.get('context_label'))}",
                    f"actor={_safe_str(row.get('actor'))}",
                    f"reference={_safe_str(row.get('reference'))}",
                    f"note={_safe_str(row.get('note'))}",
                    f"denoms={','.join(denom_summary)}",
                    f"id={_safe_str(row.get('id'))}",
                ]
            )
        )

    lines.append("")
    lines.append("=== CASH COUNTS ===")
    for row in counts:
        denom_summary = []
        for field in storage.DENOM_FIELDS:
            value = row.get(field)
            if value not in (None, "", 0):
                denom_summary.append(f"{field}={value}")

        lines.append(
            " | ".join(
                [
                    _safe_str(row["counted_at"]),
                    _safe_str(row["count_type"]),
                    f"total_eur={_format_cents(row['total_cents'])}",
                    f"account={_safe_str(row.get('cash_account_name'))}",
                    f"counted_by={_safe_str(row.get('counted_by'))}",
                    f"context={_safe_str(row.get('context_label'))}",
                    f"note={_safe_str(row.get('note'))}",
                    f"denoms={','.join(denom_summary)}",
                    f"id={_safe_str(row.get('id'))}",
                ]
            )
        )

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info(
        "Text export completed | path=%s balances=%s movements=%s counts=%s",
        text_path,
        len(balances),
        len(movements),
        len(counts),
    )


def export_all(
    db_path: Path,
    excel_path: Path,
    text_path: Path,
):
    export_excel(db_path, excel_path)
    export_text(db_path, text_path)


def import_all_from_excel(excel_path: Path) -> dict:
    if not excel_path.exists():
        return {
            "cash_accounts": [],
            "cash_contexts": [],
            "cash_movements": [],
            "cash_counts": [],
        }

    wb = load_workbook(excel_path, data_only=True)

    account_rows = _read_sheet_rows(wb, SHEET_CASH_ACCOUNTS)
    context_rows = _read_sheet_rows(wb, SHEET_CASH_CONTEXTS)
    movement_rows = _read_sheet_rows(wb, SHEET_CASH_MOVEMENTS)
    count_rows = _read_sheet_rows(wb, SHEET_CASH_COUNTS)

    imported_accounts = []
    for row in account_rows:
        imported_accounts.append(
            {
                column: row.get(column)
                for column in storage.CASH_ACCOUNT_COLUMNS
            }
        )

    imported_contexts = []
    for row in context_rows:
        imported_contexts.append(
            {
                column: row.get(column)
                for column in storage.CASH_CONTEXT_COLUMNS
            }
        )

    imported_movements = []
    for row in movement_rows:
        imported_movements.append(
            {
                column: row.get(column)
                for column in storage.CASH_MOVEMENT_COLUMNS
            }
        )

    imported_counts = []
    for row in count_rows:
        imported_counts.append(
            {
                column: row.get(column)
                for column in storage.CASH_COUNT_COLUMNS
            }
        )

    logger.info(
        "Excel import completed | path=%s accounts=%s contexts=%s movements=%s counts=%s",
        excel_path,
        len(imported_accounts),
        len(imported_contexts),
        len(imported_movements),
        len(imported_counts),
    )

    return {
        "cash_accounts": imported_accounts,
        "cash_contexts": imported_contexts,
        "cash_movements": imported_movements,
        "cash_counts": imported_counts,
    }


class CashExportService:
    export_excel = staticmethod(export_excel)
    export_text = staticmethod(export_text)
    export_all = staticmethod(export_all)
    import_all_from_excel = staticmethod(import_all_from_excel)
