import sqlite3
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from test_hunter_pricing import offer, peers, search

from flip_core.auth_store import AuthStore
from universal_v2.hunter.pricing import evaluate
from universal_v2.mobile_bridge import create_app


@pytest.fixture
def api(tmp_path, monkeypatch):
    auth = AuthStore(tmp_path / "auth.sqlite3")
    auth.init_db()
    owners = {}
    for username in ("alice", "bob"):
        # Bootstrap intentionally permits only one owner. Provision the second
        # principal in this fixture, without changing the production auth API.
        isolated = AuthStore(tmp_path / f"{username}-auth.sqlite3")
        isolated.init_db()
        owners[username] = isolated.create_owner(username, "test-password-12345")
        with (
            sqlite3.connect(isolated.path) as source,
            sqlite3.connect(auth.path) as target,
        ):
            target.execute(
                "INSERT INTO users VALUES (?,?,?,?)",
                source.execute("SELECT * FROM users").fetchone(),
            )
    monkeypatch.setenv("FLIP_API_AUTH_DB", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("FLIP_API_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("FLIP_UNIVERSAL_DEV_DIR", str(tmp_path))
    monkeypatch.setenv("FLIP_HUNTER_DB", str(tmp_path / "hunter.sqlite3"))
    monkeypatch.delenv("FLIPRADAR_READ_LEGACY_SNAPSHOTS", raising=False)
    app = create_app()
    client = TestClient(app)
    headers = {}
    for username in owners:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "test-password-12345"},
        )
        assert response.status_code == 200
        headers[username] = {
            "Authorization": "Bearer " + response.json()["access_token"]
        }
    return client, app.state.hunter, owners, headers


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/universal/searches",
        "/api/v1/universal/source-health",
        "/api/v1/universal/mobile-radar",
    ],
)
def test_every_new_read_requires_existing_bearer_auth(api, path):
    client, _, _, _ = api
    assert client.get(path).status_code == 401


def test_search_crud_is_owner_scoped_and_validated(api):
    client, store, owners, h = api
    path = "/api/v1/universal/searches/phone"
    body = {
        "name": "iPhone 14 128GB",
        "query": "iPhone 14",
        "attributes": {"storage_gb": 128},
    }
    assert client.put(path, json=body).status_code == 401
    response = client.put(path, json=body, headers=h["alice"])
    assert response.status_code == 200, response.text
    assert response.json()["owner_id"] == owners["alice"]
    assert client.get("/api/v1/universal/searches", headers=h["bob"]).json() == {
        "items": []
    }
    assert (
        client.put(
            path, json={**body, "owner_id": owners["bob"]}, headers=h["alice"]
        ).status_code
        == 403
    )
    assert (
        client.put(
            path,
            json={**body, "attributes": {"year": {"min": "bad"}}},
            headers=h["alice"],
        ).status_code
        == 422
    )
    assert (
        client.put(
            path,
            json={**body, "source_urls": {"OLX": "http://127.0.0.1/private"}},
            headers=h["alice"],
        ).status_code
        == 422
    )
    assert client.delete(path, headers=h["bob"]).status_code == 404
    assert client.delete(path, headers=h["alice"]).json() == {"deleted": True}


def test_mobile_radar_wire_contract_and_cross_owner_detail(api):
    client, store, owners, h = api
    profile = replace(search(), owner_id=owners["alice"])
    store.save_search(profile)
    candidate = offer()
    store.observe(profile.owner_id, [candidate])
    result = evaluate(candidate, profile, peers())
    store.record(profile, candidate, result, initial=False)
    page = client.get("/api/v1/universal/mobile-radar", headers=h["alice"])
    assert page.status_code == 200, page.text
    assert set(page.json()) == {"items", "next_before_id"}
    item = page.json()["items"][0]
    assert set(item) == {
        "snapshot_id",
        "title",
        "platform",
        "decision",
        "valuation",
        "observed_at",
        "price_minor",
        "url",
    }
    assert item["valuation"]["quick_sale"] == result["valuation"]["sell_minor"] / 100
    assert item["valuation"]["roi_bps"] == result["valuation"]["roi_bps"]
    assert item["valuation"]["analysis_source"] == "RULES_AND_COMPARABLES"
    detail = f"/api/v1/universal/mobile-radar/{item['snapshot_id']}"
    assert client.get(detail, headers=h["alice"]).json() == item
    assert client.get(detail, headers=h["bob"]).status_code == 404
    assert (
        client.get("/api/v1/universal/mobile-radar", headers=h["bob"]).json()["items"]
        == []
    )
    assert (
        client.get(
            "/api/v1/universal/mobile-radar?limit=101", headers=h["alice"]
        ).status_code
        == 422
    )
    # Missing legacy snapshots keep the existing 503 contract; the new store
    # never shadows or fabricates a legacy database.
    assert client.get("/api/v1/radar", headers=h["alice"]).json() == {
        "detail": "Radar database unavailable"
    }


def test_imports_do_not_claim_live_connections(api):
    client, store, owners, h = api
    profile = replace(search(), owner_id=owners["alice"])
    store.source_status(profile, "OLX", "OK", "Imported", mode="json")
    assert (
        client.get("/api/v1/universal/status", headers=h["alice"]).json()[
            "automatic_sources"
        ]
        == 0
    )
    assert (
        client.get("/api/v1/universal/source-health", headers=h["bob"]).json()["items"]
        == []
    )
