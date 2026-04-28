from core.storage import (
    create_backup,
    ensure_db_file,
    fetch_all_entries,
    get_denomination_values_from_form,
    insert_entry,
    merge_imported_entries_append_only,
    parse_optional_int,
)


def test_parse_optional_int():
    assert parse_optional_int("") is None
    assert parse_optional_int("  ") is None
    assert parse_optional_int("0") == 0
    assert parse_optional_int("5") == 5


def test_get_denomination_values_from_form():
    form = {
        "denom_100": "1",
        "denom_50": "",
        "denom_20": "0",
        "denom_10": "2",
        "denom_5": "",
        "denom_2": "1",
        "denom_1": "",
        "denom_050": "0",
        "denom_020": "",
        "denom_010": "3",
    }

    values = get_denomination_values_from_form(form)

    assert values["denom_100"] == 1
    assert values["denom_50"] is None
    assert values["denom_20"] == 0
    assert values["denom_010"] == 3


def test_insert_and_fetch_entries(temp_paths, sample_entry):
    db_path = temp_paths["db_path"]

    ensure_db_file(db_path)
    insert_entry(db_path, sample_entry)

    rows = fetch_all_entries(db_path)

    assert len(rows) == 1
    assert rows[0]["id"] == "test-id-001"
    assert rows[0]["event_name"] == "Barabend"
    assert rows[0]["denom_50"] == 1


def test_merge_imported_entries_append_only_skips_duplicates(temp_paths, sample_entry):
    db_path = temp_paths["db_path"]

    ensure_db_file(db_path)
    insert_entry(db_path, sample_entry)

    duplicate = dict(sample_entry)
    new_entry = dict(sample_entry)
    new_entry["id"] = "test-id-002"
    new_entry["event_name"] = "New Event"

    merge_imported_entries_append_only(db_path, [duplicate, new_entry])

    rows = fetch_all_entries(db_path)

    assert len(rows) == 2
    ids = {row["id"] for row in rows}
    assert ids == {"test-id-001", "test-id-002"}


def test_create_backup_creates_db_copy(temp_paths, sample_entry):
    db_path = temp_paths["db_path"]
    backup_dir = temp_paths["backup_dir"]

    ensure_db_file(db_path)
    insert_entry(db_path, sample_entry)

    backup_file = create_backup(db_path, backup_dir)

    assert backup_file.exists()
    assert backup_file.suffix == ".db"