from core import storage, sync_state
from core.cash.cash_count_request import CashCountRequest


def test_record_cash_count_sets_account_balance(
    seeded_db,
    sync_state_file,
    bar_account_id,
    cash_service_instance,
):
    result = cash_service_instance.record_count(
        CashCountRequest(
            cash_account_id=bar_account_id,
            counted_by="Jan",
            total_cents=22222,
            count_type="opening",
            context_label="Friday Bar",
            note="Opening count",
            denominations={"roll_2": 1},
        )
    )

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 22222
    assert result.count_id

    state = sync_state.load_sync_state(sync_state_file)
    assert "imported_counts" in state
    assert "imported_movements" in state


def test_record_cash_count_allows_denomination_mismatch(
    seeded_db,
    bar_account_id,
    cash_service_instance,
):
    cash_service_instance.record_count(
        CashCountRequest(
            cash_account_id=bar_account_id,
            counted_by="Jan",
            total_cents=20000,
            count_type="opening",
            context_label="Friday Bar",
            denominations={"denom_20": 1},  # 20.00 only, mismatch intentional
        )
    )

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 20000
