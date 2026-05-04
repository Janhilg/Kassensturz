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
