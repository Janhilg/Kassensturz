from core import storage


def test_create_cash_count_persists_count(seeded_db, bar_account_id):
    count_id = storage.create_cash_count(
        db_path=seeded_db,
        cash_account_id=bar_account_id,
        counted_by="Jan",
        total_cents=12345,
        count_type="opening",
        context_label="Friday Bar",
        note="Initial count",
        denominations={
            "denom_20": 2,
            "denom_10": 1,
            "roll_2": 1,
        },
    )

    counts = storage.fetch_all_cash_counts(seeded_db)
    row = next(row for row in counts if row["id"] == count_id)

    assert row["cash_account_id"] == bar_account_id
    assert row["counted_by"] == "Jan"
    assert row["total_cents"] == 12345
    assert row["count_type"] == "opening"
    assert row["context_label"] == "Friday Bar"
    assert row["note"] == "Initial count"
    assert row["denom_20"] == 2
    assert row["denom_10"] == 1
    assert row["roll_2"] == 1


def test_calculate_total_cents_from_denominations():
    total = storage.calculate_total_cents_from_denominations(
        {
            "denom_20": 2,  # 40.00
            "denom_1": 3,  # 3.00
            "denom_050": 4,  # 2.00
            "roll_2": 1,  # 50.00
            "roll_1": 1,  # 25.00
        }
    )

    assert total == 12000


def test_merge_imported_cash_counts_append_only(seeded_db, bar_account_id):
    count_id = storage.create_cash_count(
        db_path=seeded_db,
        cash_account_id=bar_account_id,
        counted_by="Jan",
        total_cents=10000,
        count_type="opening",
        context_label="Friday Bar",
    )

    imported = [
        {
            "id": count_id,
            "context_id": None,
            "context_label": "Friday Bar",
            "cash_account_id": bar_account_id,
            "counted_at": "2026-04-30T10:00:00",
            "count_type": "opening",
            "counted_by": "Jan",
            "total_cents": 10000,
            "note": "",
            **{field: None for field in storage.DENOM_FIELDS},
        },
        {
            "id": "count-2",
            "context_id": None,
            "context_label": "Friday Bar",
            "cash_account_id": bar_account_id,
            "counted_at": "2026-04-30T12:00:00",
            "count_type": "closing",
            "counted_by": "Jan",
            "total_cents": 15000,
            "note": "",
            **{field: None for field in storage.DENOM_FIELDS},
            "cash_account_name": "Bar Cash Box",
        },
    ]

    result = storage.merge_imported_cash_counts_append_only(seeded_db, imported)

    assert result["imported"] == 1
    assert result["skipped"] == 1

    counts = storage.fetch_all_cash_counts(seeded_db)
    assert len(counts) == 2
