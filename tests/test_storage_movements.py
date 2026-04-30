from core import storage


def test_create_cash_movement_persists_movement(
    seeded_db,
    bar_account_id,
    runner_account_id,
):
    movement_id = storage.create_cash_movement(
        db_path=seeded_db,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="REF-1",
        note="Float transfer",
        denominations={
            "denom_20": 1,
            "denom_10": 1,
            "roll_1": 1,
        },
    )

    movements = storage.fetch_all_cash_movements(seeded_db)
    row = next(row for row in movements if row["id"] == movement_id)

    assert row["from_account_id"] == bar_account_id
    assert row["to_account_id"] == runner_account_id
    assert row["amount_cents"] == 5000
    assert row["context_label"] == "Friday Bar"
    assert row["actor"] == "Jan"
    assert row["reference"] == "REF-1"
    assert row["note"] == "Float transfer"
    assert row["denom_20"] == 1
    assert row["denom_10"] == 1
    assert row["roll_1"] == 1


def test_merge_imported_cash_movements_append_only(
    seeded_db,
    bar_account_id,
    runner_account_id,
):
    existing_id = storage.create_cash_movement(
        db_path=seeded_db,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
    )

    imported = [
        {
            "id": existing_id,
            "context_id": None,
            "context_label": "Friday Bar",
            "effective_at": "2026-04-30T10:00:00",
            "created_at": "2026-04-30T10:00:00",
            "from_account_id": bar_account_id,
            "to_account_id": runner_account_id,
            "amount_cents": 5000,
            "actor": "",
            "reference": "",
            "note": "",
            **{field: None for field in storage.DENOM_FIELDS},
        },
        {
            "id": "mov-2",
            "context_id": None,
            "context_label": "Friday Bar",
            "effective_at": "2026-04-30T11:00:00",
            "created_at": "2026-04-30T11:00:00",
            "from_account_id": bar_account_id,
            "to_account_id": runner_account_id,
            "amount_cents": 2000,
            "actor": "",
            "reference": "",
            "note": "",
            **{field: None for field in storage.DENOM_FIELDS},
            "from_account_name": "Bar Cash Box",
            "to_account_name": "Runner Float",
        },
    ]

    result = storage.merge_imported_cash_movements_append_only(seeded_db, imported)

    assert result["imported"] == 1
    assert result["skipped"] == 1

    movements = storage.fetch_all_cash_movements(seeded_db)
    assert len(movements) == 2