import app as app_module


def test_index_get(client):
    response = client.get("/")
    assert response.status_code == 200


def test_index_renders_account_translation_keys(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert 'data-i18n="account_bar_cash_box"' in body
    assert 'data-i18n="Bar Cash Box"' not in body


def test_balances_get(client):
    response = client.get("/balances")
    assert response.status_code == 200


def test_cash_movement_get(client):
    response = client.get("/cash/movement")
    assert response.status_code == 200


def test_cash_movement_renders_account_translation_keys_for_both_selects(client):
    response = client.get("/cash/movement")
    body = response.get_data(as_text=True)

    assert body.count('data-i18n="account_runner_float"') == 2


def test_index_post_uses_web_app_count_service(client, monkeypatch):
    account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE,
        "Bar Cash Box",
    )
    calls = []

    def fake_record_cash_count(count_request):
        calls.append(count_request)
        return {"imported_counts": 0, "imported_movements": 0, "count_id": "count-2"}

    monkeypatch.setattr(
        app_module.web_app,
        "record_cash_count",
        fake_record_cash_count,
    )

    response = client.post(
        "/",
        data={
            "cash_account_id": account["id"],
            "counted_by": "Jan",
            "count_type": "opening",
            "context_label": "Friday Bar",
            "note": "Opening count",
            "total_eur": "123.45",
        },
    )

    assert response.status_code == 302
    assert calls[0].cash_account_id == account["id"]
    assert calls[0].total_cents == 12345
    assert calls[0].context_label == "Friday Bar"


def test_cash_movement_post_uses_web_app_movement_service(client, monkeypatch):
    from_account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE,
        "Bar Cash Box",
    )
    to_account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE,
        "Runner Float",
    )
    calls = []

    def fake_record_cash_movement(movement_request):
        calls.append(movement_request)
        return {
            "imported_counts": 0,
            "imported_movements": 0,
            "movement_id": "movement-2",
        }

    monkeypatch.setattr(
        app_module.web_app,
        "record_cash_movement",
        fake_record_cash_movement,
    )

    response = client.post(
        "/cash/movement",
        data={
            "from_account_id": from_account["id"],
            "to_account_id": to_account["id"],
            "amount_eur": "50.00",
            "context_label": "Friday Bar",
            "actor": "Jan",
            "reference": "REF-1",
            "note": "Float transfer",
        },
    )

    assert response.status_code == 302
    assert calls[0].from_account_id == from_account["id"]
    assert calls[0].to_account_id == to_account["id"]
    assert calls[0].amount_cents == 5000
    assert calls[0].context_label == "Friday Bar"
