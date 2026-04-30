from core import cash_service, storage



def test_record_cash_movement_adjusts_balances(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
    runner_account_id,
    monkeypatch,
):
    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 20000)
    storage.set_cash_account_balance_cents(seeded_db, runner_account_id, 1000)

    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="REF-1",
        note="Float transfer",
        denominations={"denom_20": 1, "denom_10": 1},
    )

    bar = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = storage.fetch_cash_account_by_id(seeded_db, runner_account_id)

    assert bar["current_balance_cents"] == 15000
    assert runner["current_balance_cents"] == 6000


def test_record_cash_movement_requires_source_or_target(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    monkeypatch,
):
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    try:
        cash_service.record_cash_movement_and_sync(
            db_path=seeded_db,
            excel_path=excel_path,
            text_path=text_path,
            backup_dir=backup_dir,
            sync_state_file=sync_state_file,
            config=config_stub,
            from_account_id=None,
            to_account_id=None,
            amount_cents=5000,
            context_label="Friday Bar",
        )
    except ValueError as exc:
        assert "source or target" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_runner_purchase_auto_returns_remaining_change_to_bar(
        seeded_db,
        excel_path,
        text_path,
        backup_dir,
        sync_state_file,
        config_stub,
        bar_account_id,
        runner_account_id,
        supplier_account_id,
        monkeypatch,
):
    # Start with Bar = 100€, Runner = 0€
    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    storage.set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    # First movement: Bar gives Runner 50€
    cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    # Mock sync so the second call stays local/test-only
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    # Second movement: Runner spends 37€ at supplier
    result = cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=3700,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Drinks purchase",
        denominations=None,
    )

    # Auto-return should have happened for 13€
    assert result["auto_return"] is not None
    assert result["auto_return"]["amount_cents"] == 1300

    # Final balances:
    # Bar: 100 - 50 + 13 = 63
    # Runner: 0
    # Supplier: 37
    bar = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = storage.fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = storage.fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 6300
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 3700

    # There should be 3 movements total:
    # 1) Bar -> Runner (50)
    # 2) Runner -> Supplier (37)
    # 3) Runner -> Bar (13) [auto-return]
    movements = storage.fetch_all_cash_movements(seeded_db)
    assert len(movements) == 3

    auto_return = [
        m for m in movements
        if m["from_account_id"] == runner_account_id
           and m["to_account_id"] == bar_account_id
           and m["amount_cents"] == 1300
    ]
    assert len(auto_return) == 1
    assert "Auto-return" in (auto_return[0]["note"] or "")

def test_runner_purchase_with_exact_amount_creates_no_auto_return(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    monkeypatch,
):
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    storage.set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Exact supplier purchase",
        denominations=None,
    )

    assert result["auto_return"] is None

    bar = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = storage.fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = storage.fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 5000
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 5000

    movements = storage.fetch_all_cash_movements(seeded_db)
    assert len(movements) == 2

def test_runner_purchase_auto_returns_remaining_balance_after_purchase(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    monkeypatch,
):
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 20000)
    storage.set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=10000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    result = cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=3000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Supplier purchase",
        denominations=None,
    )

    assert result["auto_return"] is not None
    assert result["auto_return"]["amount_cents"] == 7000

    bar = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = storage.fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = storage.fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 17000
    assert runner["current_balance_cents"] == 0
    assert supplier["current_balance_cents"] == 3000

    movements = storage.fetch_all_cash_movements(seeded_db)
    assert len(movements) == 3

def test_runner_purchase_can_overspend_and_leave_negative_runner_balance(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
    runner_account_id,
    supplier_account_id,
    monkeypatch,
):
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "download_remote_excel_if_exists",
        lambda local_excel_path, config: False,
    )
    monkeypatch.setattr(
        cash_service.nextcloud_sync,
        "upload_files",
        lambda excel_path, text_path, config: {"uploaded": False},
    )

    storage.set_cash_account_balance_cents(seeded_db, bar_account_id, 10000)
    storage.set_cash_account_balance_cents(seeded_db, runner_account_id, 0)

    # Bar gives runner 50€
    cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=bar_account_id,
        to_account_id=runner_account_id,
        amount_cents=5000,
        context_label="Friday Bar",
        actor="Jan",
        reference="FLOAT-1",
        note="Give runner cash",
        denominations=None,
    )

    # Runner spends 60€ -> 10€ personal money added
    result = cash_service.record_cash_movement_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        from_account_id=runner_account_id,
        to_account_id=supplier_account_id,
        amount_cents=6000,
        context_label="Friday Bar",
        actor="Jan",
        reference="RECEIPT-1",
        note="Runner added personal money",
        denominations=None,
    )

    # No auto-return because runner balance is negative
    assert result["auto_return"] is None

    bar = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    runner = storage.fetch_cash_account_by_id(seeded_db, runner_account_id)
    supplier = storage.fetch_cash_account_by_id(seeded_db, supplier_account_id)

    assert bar["current_balance_cents"] == 5000
    assert runner["current_balance_cents"] == -1000
    assert supplier["current_balance_cents"] == 6000

    movements = storage.fetch_all_cash_movements(seeded_db)
    assert len(movements) == 2