import config
from core.storage_accounts import (
    fetch_cash_account_by_id,
    merge_imported_cash_accounts_append_only,
)
from core.storage_contexts import (
    fetch_cash_context_by_id,
    merge_imported_cash_contexts_append_only,
)
from core.storage_counts import fetch_all_cash_counts, merge_imported_cash_counts_append_only
from core.storage_movements import (
    fetch_all_cash_movements,
    merge_imported_cash_movements_append_only,
)
from core.storage_schema import DENOM_FIELDS


def test_merge_imported_cash_accounts_defaults_live_fields_and_is_idempotent(seeded_db):
    imported_accounts = [
        {
            "id": "remote-cash-box",
            "name": "Remote Cash Box",
            "account_type": config.Config.ACCOUNT_TYPE_CASH_BOX,
            "current_balance_cents": 99999,
            "is_active": None,
            "sort_order": None,
            "created_at": "",
        }
    ]

    first_result = merge_imported_cash_accounts_append_only(seeded_db, imported_accounts)
    second_result = merge_imported_cash_accounts_append_only(seeded_db, imported_accounts)

    assert first_result == {
        "imported": 1,
        "skipped": 0,
        "matched_by_name": 0,
        "total": 1,
    }
    assert second_result == {
        "imported": 0,
        "skipped": 1,
        "matched_by_name": 0,
        "total": 1,
    }

    account = fetch_cash_account_by_id(seeded_db, "remote-cash-box")
    assert account["name"] == "Remote Cash Box"
    assert account["current_balance_cents"] == 0
    assert account["is_active"] == 1
    assert account["sort_order"] == 0
    assert account["created_at"]


def test_merge_imported_cash_contexts_defaults_missing_fields_and_is_idempotent(seeded_db):
    imported_contexts = [
        {
            "id": "remote-context",
            "label": "Remote Event",
            "created_at": "",
            "last_used_at": "",
            "is_active": None,
        },
        {
            "id": "missing-label-context",
            "label": "",
            "created_at": "2026-05-04T12:00:00",
            "last_used_at": "2026-05-04T12:00:00",
            "is_active": 1,
        },
    ]

    first_result = merge_imported_cash_contexts_append_only(seeded_db, imported_contexts)
    second_result = merge_imported_cash_contexts_append_only(seeded_db, imported_contexts)

    assert first_result == {"imported": 1, "skipped": 1, "total": 2}
    assert second_result == {"imported": 0, "skipped": 2, "total": 2}

    context = fetch_cash_context_by_id(seeded_db, "remote-context")
    assert context["label"] == "Remote Event"
    assert context["created_at"]
    assert context["last_used_at"] == context["created_at"]
    assert context["is_active"] == 1
    assert fetch_cash_context_by_id(seeded_db, "missing-label-context") is None


def test_merge_imported_cash_counts_remaps_by_account_name_and_is_idempotent(
    seeded_db,
    bar_account_id,
):
    imported_counts = [
        {
            "id": "remote-count",
            "context_id": "remote-context-not-present",
            "context_label": "Remote Event",
            "cash_account_id": "remote-bar-id",
            "cash_account_name": "Bar Cash Box",
            "counted_at": "2026-05-04T12:00:00",
            "count_type": "closing",
            "counted_by": "Jan",
            "total_cents": 12345,
            "note": "remote import",
            **{field: None for field in DENOM_FIELDS},
        }
    ]

    first_result = merge_imported_cash_counts_append_only(seeded_db, imported_counts)
    second_result = merge_imported_cash_counts_append_only(seeded_db, imported_counts)

    assert first_result == {
        "imported": 1,
        "skipped": 0,
        "remapped": 1,
        "total": 1,
    }
    assert second_result == {
        "imported": 0,
        "skipped": 1,
        "remapped": 0,
        "total": 1,
    }

    counts = fetch_all_cash_counts(seeded_db)
    assert len(counts) == 1
    assert counts[0]["id"] == "remote-count"
    assert counts[0]["cash_account_id"] == bar_account_id
    assert counts[0]["context_id"] is None
    assert counts[0]["total_cents"] == 12345


def test_merge_imported_cash_movements_remaps_by_account_names_and_is_idempotent(
    seeded_db,
    bar_account_id,
    runner_account_id,
):
    imported_movements = [
        {
            "id": "remote-movement",
            "context_id": "remote-context-not-present",
            "context_label": "Remote Event",
            "effective_at": "2026-05-04T12:00:00",
            "created_at": "2026-05-04T12:01:00",
            "from_account_id": "remote-bar-id",
            "from_account_name": "Bar Cash Box",
            "to_account_id": "remote-runner-id",
            "to_account_name": "Runner Float",
            "amount_cents": 5000,
            "actor": "Jan",
            "reference": "remote-ref",
            "note": "remote import",
            **{field: None for field in DENOM_FIELDS},
        }
    ]

    first_result = merge_imported_cash_movements_append_only(seeded_db, imported_movements)
    second_result = merge_imported_cash_movements_append_only(seeded_db, imported_movements)

    assert first_result == {
        "imported": 1,
        "skipped": 0,
        "remapped": 2,
        "total": 1,
    }
    assert second_result == {
        "imported": 0,
        "skipped": 1,
        "remapped": 0,
        "total": 1,
    }

    movements = fetch_all_cash_movements(seeded_db)
    assert len(movements) == 1
    assert movements[0]["id"] == "remote-movement"
    assert movements[0]["from_account_id"] == bar_account_id
    assert movements[0]["to_account_id"] == runner_account_id
    assert movements[0]["context_id"] is None
    assert movements[0]["amount_cents"] == 5000
