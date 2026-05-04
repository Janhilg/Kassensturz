import app as app_module


def _login_admin(client):
    with client.session_transaction() as session:
        session["admin_logged_in"] = True


def test_admin_routes_redirect_to_login_when_not_authenticated(client):
    for route in (
        "/admin",
        "/admin/rebuild-exports",
        "/admin/sync-now",
        "/admin/restore-backup",
    ):
        method = client.post if route != "/admin" else client.get
        response = method(route)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/admin/login")


def test_admin_rebuild_exports_success_flashes_result(client, monkeypatch):
    calls = []

    def fake_rebuild_exports():
        calls.append("rebuild")
        return {"imported_counts": 2, "imported_movements": 3}

    monkeypatch.setattr(app_module.web_app, "rebuild_exports", fake_rebuild_exports)
    _login_admin(client)

    response = client.post("/admin/rebuild-exports", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls == ["rebuild"]
    assert "Rebuild + sync complete." in body
    assert "Imported counts: 2, imported movements: 3." in body


def test_admin_rebuild_exports_error_flashes_message(client, monkeypatch):
    def fake_rebuild_exports():
        raise RuntimeError("rebuild exploded")

    monkeypatch.setattr(app_module.web_app, "rebuild_exports", fake_rebuild_exports)
    _login_admin(client)

    response = client.post("/admin/rebuild-exports", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Rebuild failed: rebuild exploded" in body


def test_admin_sync_now_success_flashes_result(client, monkeypatch):
    calls = []

    class SyncResult:
        def to_dict(self):
            calls.append("to_dict")
            return {"imported_counts": 4, "imported_movements": 5}

    monkeypatch.setattr(app_module.web_app, "rebuild_exports", lambda: SyncResult())
    _login_admin(client)

    response = client.post("/admin/sync-now", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls == ["to_dict"]
    assert "Sync complete." in body
    assert "Imported counts: 4, imported movements: 5." in body


def test_admin_sync_now_error_flashes_message(client, monkeypatch):
    def fake_rebuild_exports():
        raise RuntimeError("sync exploded")

    monkeypatch.setattr(app_module.web_app, "rebuild_exports", fake_rebuild_exports)
    _login_admin(client)

    response = client.post("/admin/sync-now", follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Sync failed: sync exploded" in body


def test_admin_restore_backup_delegates_restore_and_rebuild(client, monkeypatch):
    calls = []

    def fake_restore_backup(**kwargs):
        calls.append(("restore", kwargs["backup_file"]))

    def fake_rebuild_exports():
        calls.append(("rebuild",))
        return {"imported_counts": 0, "imported_movements": 0}

    monkeypatch.setattr(app_module.web_app.storage, "restore_backup", fake_restore_backup)
    monkeypatch.setattr(app_module.web_app, "rebuild_exports", fake_rebuild_exports)
    _login_admin(client)

    response = client.post(
        "/admin/restore-backup",
        data={"backup_name": "kassensturz_backup_20260504_080000.db"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls == [
        (
            "restore",
            app_module.web_app.paths.backup_dir / "kassensturz_backup_20260504_080000.db",
        ),
        ("rebuild",),
    ]
    assert "Backup restored: kassensturz_backup_20260504_080000.db" in body


def test_admin_restore_backup_missing_selection_flashes_error(client, monkeypatch):
    def fake_restore_backup(**kwargs):
        raise AssertionError("restore should not be called")

    monkeypatch.setattr(app_module.web_app.storage, "restore_backup", fake_restore_backup)
    _login_admin(client)

    response = client.post(
        "/admin/restore-backup",
        data={"backup_name": ""},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Restore failed: No backup selected." in body
