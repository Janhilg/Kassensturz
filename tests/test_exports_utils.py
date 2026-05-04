from datetime import date, time

from openpyxl import Workbook

from core import export_utils, storage


def test_export_and_import_roundtrip(
    seeded_db,
    excel_path,
    text_path,
    bar_account_id,
    runner_account_id,
):
    storage.create_cash_count(
        db_path=seeded_db,
        cash_account_id=bar_account_id,
        counted_by="Jan",
        total_cents=12345,
        count_type="opening",
        context_label="Friday Bar",
        denominations={"roll_2": 1},
    )

    storage.create_cash_movement(
        db_path=seeded_db,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        denominations={"denom_20": 1, "denom_10": 1},
    )

    export_utils.export_all(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
    )

    assert excel_path.exists()
    assert text_path.exists()

    imported = export_utils.import_all_from_excel(excel_path)

    assert "cash_accounts" in imported
    assert "cash_contexts" in imported
    assert "cash_counts" in imported
    assert "cash_movements" in imported

    assert len(imported["cash_counts"]) == 1
    assert len(imported["cash_movements"]) == 1

    count_row = imported["cash_counts"][0]
    movement_row = imported["cash_movements"][0]

    assert count_row["total_cents"] == 12345
    assert count_row["roll_2"] == 1

    assert movement_row["amount_cents"] == 5000
    assert movement_row["denom_20"] == 1
    assert movement_row["denom_10"] == 1


def test_import_legacy_cash_count_workbook(tmp_path):
    excel_path = tmp_path / "legacy.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Production"
    worksheet.append(
        [
            "Date",
            "Timestamp",
            "Event name",
            "Counted by",
            "Cash sum",
            "Event status",
            "Comment",
        ]
    )
    worksheet.append(
        [
            date(2026, 4, 30),
            time(23, 45),
            "Friday Bar",
            "Jan",
            "1.234,56 €",
            "Closed",
            "legacy closing count",
        ]
    )
    workbook.save(excel_path)

    imported = export_utils.import_all_from_excel(excel_path)

    assert imported["source_format"] == "legacy_cash_counts"
    assert len(imported["cash_contexts"]) == 1
    assert imported["cash_contexts"][0]["label"] == "Friday Bar"
    assert len(imported["cash_counts"]) == 1

    count = imported["cash_counts"][0]
    assert count["cash_account_id"] == "acc_bar_cash_box"
    assert count["cash_account_name"] == "Bar Cash Box"
    assert count["counted_at"] == "2026-04-30T23:45:00"
    assert count["counted_by"] == "Jan"
    assert count["total_cents"] == 123456
    assert count["count_type"] == "closing"
    assert count["note"] == "legacy closing count"
