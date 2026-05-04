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
