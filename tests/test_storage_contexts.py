from core import storage


def test_get_or_create_cash_context_creates_context(seeded_db):
    context_id, label = storage.get_or_create_cash_context(seeded_db, "Friday Bar")

    assert context_id is not None
    assert label == "Friday Bar"


def test_get_or_create_cash_context_reuses_existing_context(seeded_db):
    first_id, _ = storage.get_or_create_cash_context(seeded_db, "Friday Bar")
    second_id, _ = storage.get_or_create_cash_context(seeded_db, "Friday Bar")

    assert first_id == second_id


def test_get_latest_cash_context_label(seeded_db):
    assert storage.get_latest_cash_context_label(seeded_db) == ""

    storage.get_or_create_cash_context(seeded_db, "Friday Bar")
    assert storage.get_latest_cash_context_label(seeded_db) == "Friday Bar"