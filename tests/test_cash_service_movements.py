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