import pytest
from fastapi.testclient import TestClient

from flip_core.auth_store import AuthStore
from universal_v2.portal.web import create_app


def test_single_origin_static_export_routes_and_api_do_not_overlap(
    tmp_path, monkeypatch
):
    root = tmp_path / "web"
    root.mkdir()
    (root / "index.html").write_text("<html><h1>FlipRadar</h1></html>")
    (root / "account.html").write_text("<html><h1>Konto</h1></html>")
    (root / ".env").write_text("NEVER_PUBLIC=test")
    (root / "config.py").write_text("not_a_public_asset = True")
    (root / "data.sqlite3").write_bytes(b"not a real database")
    (root / "_expo").mkdir()
    (root / "_expo" / "app.js").write_text('console.log("test")')
    auth = AuthStore(tmp_path / "auth.sqlite3")
    auth.init_db()
    auth.create_owner("owner", "safe-owner-password-123")
    for key, value in {
        "FLIP_API_AUTH_DB": str(auth.path),
        "FLIP_API_DATA_ROOT": str(tmp_path),
        "FLIP_UNIVERSAL_DEV_DIR": str(tmp_path),
        "FLIP_HUNTER_DB": str(tmp_path / "hunter.sqlite3"),
        "FLIP_PORTAL_ENABLED": "1",
        "FLIP_PORTAL_WEB_ROOT": str(root),
    }.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert "<h1>Konto</h1>" in client.get("/account").text
    assert client.get("/_expo/app.js").status_code == 200
    assert client.get("/offer/snap-123").status_code == 200
    assert (
        client.get("/api/v1/public/config")
        .headers["content-type"]
        .startswith("application/json")
    )
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/account-private-file.txt").status_code == 404
    assert client.get("/%2e%2e/auth.sqlite3").status_code == 404
    for secret in (".env", "config.py", "data.sqlite3"):
        assert client.get("/" + secret).status_code == 404


def test_static_export_required_before_serving(tmp_path, monkeypatch):
    monkeypatch.setenv("FLIP_PORTAL_WEB_ROOT", str(tmp_path / "missing"))
    with pytest.raises(RuntimeError):
        create_app()
