import config
from core import storage


def test_seed_default_cash_accounts_creates_expected_accounts(seeded_db):
    accounts = storage.fetch_all_cash_accounts(seeded_db, active_only=False)
    names = {row["name"] for row in accounts}

    config_names = {row[1] for row in config.Config.DEFAULT_CASH_ACCOUNTS}

    for name, config_name in names - config_names:
        assert name == config_name

def test_seed_default_cash_accounts_is_idempotent(seeded_db):
    before = storage.fetch_all_cash_accounts(seeded_db, active_only=False)
    storage.seed_default_cash_accounts(seeded_db)
    after = storage.fetch_all_cash_accounts(seeded_db, active_only=False)

    assert len(before) == len(after)


def test_set_cash_account_balance_cents(seeded_db, bar_account_id):
    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 12345)

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 12345


def test_adjust_cash_account_balance_cents(seeded_db, bar_account_id):
    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    storage.adjust_cash_account_balance_cents(seeded_db, bar_account_id, -2500)
    storage.adjust_cash_account_balance_cents(seeded_db, bar_account_id, 500)

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 8000


def test_fetch_cash_account_balances_uses_current_balance_cents(seeded_db, bar_account_id):
    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 7777)

    balances = storage.fetch_cash_account_balances(seeded_db)
    bar = next(row for row in balances if row["id"] == bar_account_id)

    assert bar["balance_cents"] == 7777
    assert bar["balance_eur"] == 77.77