import app as app_module


def test_index_post_count(client):
    account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE, "Bar Cash Box"
    )
    assert account is not None

    response = client.post(
        "/",
        data={
            "cash_account_id": account["id"],
            "counted_by": "Jan",
            "count_type": "opening",
            "context_label": "Friday Bar",
            "note": "Opening count",
            "total_eur": "123.45",
            "denom_100": "",
            "denom_50": "",
            "denom_20": "",
            "denom_10": "",
            "denom_5": "",
            "denom_2": "",
            "denom_1": "",
            "denom_050": "",
            "denom_020": "",
            "denom_010": "",
            "roll_2": "",
            "roll_1": "",
            "roll_050": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_cash_movement_post(client):
    from_account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE, "Bar Cash Box"
    )
    to_account = app_module.storage.fetch_cash_account_by_name(
        app_module.LOCAL_DB_FILE, "Runner Float"
    )
    assert from_account is not None
    assert to_account is not None

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
            "denom_100": "",
            "denom_50": "",
            "denom_20": "",
            "denom_10": "",
            "denom_5": "",
            "denom_2": "",
            "denom_1": "",
            "denom_050": "",
            "denom_020": "",
            "denom_010": "",
            "roll_2": "",
            "roll_1": "",
            "roll_050": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_admin_login_and_admin_page(client):
    response = client.post(
        "/admin/login",
        data={"password": app_module.Config.ADMIN_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.get("/admin")
    assert response.status_code == 200


def test_admin_page_shows_bootstrap_status(client):
    client.post(
        "/admin/login",
        data={"password": app_module.Config.ADMIN_PASSWORD},
        follow_redirects=True,
    )

    response = client.get("/admin")
    body = response.get_data(as_text=True)

    assert "Production Bootstrap" in body
    assert "App is not running in production mode" in body
