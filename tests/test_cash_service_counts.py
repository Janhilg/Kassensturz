from core import cash_service, storage, sync_state


def test_record_cash_count_sets_account_balance(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
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

    result = cash_service.record_cash_count_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        cash_account_id=bar_account_id,
        counted_by="Jan",
        total_cents=22222,
        count_type="opening",
        context_label="Friday Bar",
        note="Opening count",
        denominations={"roll_2": 1},
    )

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 22222
    assert "count_id" in result

    state = sync_state.load_sync_state(sync_state_file)
    assert "imported_counts" in state
    assert "imported_movements" in state


def test_record_cash_count_allows_denomination_mismatch(
    seeded_db,
    excel_path,
    text_path,
    backup_dir,
    sync_state_file,
    config_stub,
    bar_account_id,
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

    cash_service.record_cash_count_and_sync(
        db_path=seeded_db,
        excel_path=excel_path,
        text_path=text_path,
        backup_dir=backup_dir,
        sync_state_file=sync_state_file,
        config=config_stub,
        cash_account_id=bar_account_id,
        counted_by="Jan",
        total_cents=20000,
        count_type="opening",
        context_label="Friday Bar",
        denominations={"denom_20": 1},  # 20.00 only, mismatch intentional
    )

    account = storage.fetch_cash_account_by_id(seeded_db, bar_account_id)
    assert account["current_balance_cents"] == 20000