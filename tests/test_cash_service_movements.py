import pytest

from core.cash.cash_movement_request import CashMovementRequest
from core.storage_accounts import (
    fetch_cash_account_by_id,
    set_cash_account_balance_cents,
)
from core.storage_movements import fetch_all_cash_movements


def _record_movement(cash_service_instance, **kwargs):
    return cash_service_instance.record_movement(CashMovementRequest(**kwargs))


def test_record_cash_movement_adjusts_balances(
    seeded_db,
    bar_account_id,
    runner_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 20000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 1000)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="REF-1",
        note="Float transfer",
        denominations={"denom_20": 1, "denom_10": 1},
    )

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)

    assert bar["current_balance_cents"] == 15000
    assert runner["current_balance_cents"] == 6000


def test_record_cash_movement_requires_source_or_target(cash_service_instance):
    with pytest.raises(ValueError, match="source or target"):
        _record_movement(
            cash_service_instance,
            from_account_id=None,
            to_account_id=None,
            amount_cents=5000,
            context_label="Friday Bar",
        )


def test_runner_purchase_auto_returns_remaining_change_to_bar(
    seeded_db,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = _record_movement(
        cash_service_instance,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=3700,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Drinks purchase",
        denominations=None,
    )

    assert result.auto_return is not None
    assert result.auto_return["amount_cents"] == 1300

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 6300
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 3700

    movements = fetch_all_cash_movements(seeded_db)
    assert len(movements) == 3

    auto_return = [
        movement
        for movement in movements
        if movement["from_account_id"] == runner_account_id
        and movement["to_account_id"] == bar_account_id
        and movement["amount_cents"] == 1300
    ]
    assert len(auto_return) == 1
    assert "Auto-return" in (auto_return[0]["note"] or "")


def test_runner_purchase_with_exact_amount_creates_no_auto_return(
    seeded_db,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = _record_movement(
        cash_service_instance,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Exact supplier purchase",
        denominations=None,
    )

    assert result.auto_return is None

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 5000
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 5000

    movements = fetch_all_cash_movements(seeded_db)
    assert len(movements) == 2


def test_runner_purchase_auto_returns_remaining_balance_after_purchase(
    seeded_db,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 20000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=10000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = _record_movement(
        cash_service_instance,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=3000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Supplier purchase",
        denominations=None,
    )

    assert result.auto_return is not None
    assert result.auto_return["amount_cents"] == 7000

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 17000
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 3000

    movements = fetch_all_cash_movements(seeded_db)
    assert len(movements) == 3


def test_runner_purchase_can_overspend_and_leave_negative_runner_balance(
    seeded_db,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = _record_movement(
        cash_service_instance,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=6000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Runner added personal money",
        denominations=None,
    )

    assert result.auto_return is None

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 5000
    assert runner["current_balance_cents"] == -1000
    assert supplier["current_balance_cents"] == 6000

    movements = fetch_all_cash_movements(seeded_db)
    assert len(movements) == 2


def test_runner_can_be_reimbursed_after_overspending(
    seeded_db,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    cash_service_instance,
):
    set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    _record_movement(
        cash_service_instance,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=6000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Runner added personal money",
        denominations=None,
    )

    _record_movement(
        cash_service_instance,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=1000,
        context_label="Friday Bar",
        actor="Jan",
        reference="REPAY-1",
        note="Reimburse runner personal money",
        denominations=None,
    )

    bar = fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 4000
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 6000
