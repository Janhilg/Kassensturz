import app as app_module


def test_index_get(client):
    response = client.get("/")
    assert response.status_code == 200


def test_balances_get(client):
    response = client.get("/balances")
    assert response.status_code == 200


def test_cash_movement_get(client):
    response = client.get("/cash/movement")
    assert response.status_code == 200