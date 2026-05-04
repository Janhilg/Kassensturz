import config
from core.storage_accounts import (
    adjust_cash_account_balance_cents,
    fetch_all_cash_accounts,
    fetch_cash_account_balances,
    fetch_cash_account_by_id,
    insert_cash_account,
    merge_imported_cash_accounts_append_only,
    seed_default_cash_accounts,
    set_cash_account_balance_cents,
)
from core.storage_migrations import ensure_db_file


def test_seed_default_cash_accounts_creates_expected_accounts(seeded_db):
    accounts = fetch_all_cash_accounts(seeded_db, active_only=False)
    names = {row["name"] for row in accounts}

    config_names = {row[1] for row in config.Config.DEFAULT_CASH_ACCOUNTS}

    for name, config_name in names - config_names:
        assert name == config_name


def test_seed_default_cash_accounts_is_idempotent(seeded_db):
    before = fetch_all_cash_accounts(seeded_db, active_only=False)
    seed_default_cash_accounts(seeded_db)
    after = fetch_all_cash_accounts(seeded_db, active_only=False)

    assert len(before) == len(after)


def test_seed_default_cash_accounts_repairs_translation_key_names(db_path):
    ensure_db_file(db_path)
    insert_cash_account(
        db_path=db_path,
        account_id="acc_bar_cash_box",
        name="account_bar_cash_box",
        account_type=config.Config.ACCOUNT_TYPE_CASH_BOX,
        sort_order=20,
    )

    seed_default_cash_accounts(db_path)

    account = fetch_cash_account_by_id(db_path, "acc_bar_cash_box")
    assert account["name"] == "Bar Cash Box"


def test_merge_imported_cash_accounts_skips_duplicate_ids_and_names(seeded_db):
    imported = [
        {
            "id": "acc_bar_cash_box",
            "name": "Bar Cash Box",
            "account_type": config.Config.ACCOUNT_TYPE_CASH_BOX,
            "current_balance_cents": 99999,
            "is_active": 1,
            "sort_order": 20,
            "created_at": "2026-05-04T08:00:00",
        },
        {
            "id": "remote-bar-copy",
            "name": "Bar Cash Box",
            "account_type": config.Config.ACCOUNT_TYPE_CASH_BOX,
            "current_balance_cents": 99999,
            "is_active": 1,
            "sort_order": 21,
            "created_at": "2026-05-04T08:01:00",
        },
    ]

    result = merge_imported_cash_accounts_append_only(seeded_db, imported)

    assert result["imported"] == 0
    assert result["skipped"] == 2
    assert result["matched_by_name"] == 1
    assert fetch_cash_account_by_id(seeded_db, "remote-bar-copy") is None


def test_set_cash_account_balance_cents(seeded_db, bar_account_id):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 12345)

    account = fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 12345


def test_adjust_cash_account_balance_cents(seeded_db, bar_account_id):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    adjust_cash_account_balance_cents(seeded_db, bar_account_id, -2500)
    adjust_cash_account_balance_cents(seeded_db, bar_account_id, 500)

    account = fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 8000


def test_fetch_cash_account_balances_uses_current_balance_cents(seeded_db, bar_account_id):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 7777)

    balances = fetch_cash_account_balances(seeded_db)
    bar = next(row for row in balances if row["id"] == bar_account_id)

    assert bar["balance_cents"] == 7777
    assert bar["balance_eur"] == 77.77
