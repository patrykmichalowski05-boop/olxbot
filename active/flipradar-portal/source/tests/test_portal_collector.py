from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_hunter_pricing import offer, peers, search

from examples.generate_portal_demo import create_demo
from flip_core.auth_store import AuthStore
from universal_v2.hunter.runner import Runner
from universal_v2.hunter.store import Store
from universal_v2.portal.collector import scan_accounts
from universal_v2.portal.store import AccessDenied, PortalStore


@pytest.fixture
def portal(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3")
    auth.init_db()
    owner = auth.create_owner("owner", "safe-owner-password-123")
    return PortalStore(Store(tmp_path / "hunter.sqlite3"), auth, owner), owner


def test_collector_skips_expired_disabled_and_unprovisioned_accounts(portal):
    service, owner = portal
    users = {
        name: service.register(name, "safe-member-password-123")
        for name in ("starter", "paid", "expired", "blocked")
    }
    service.grant(users["paid"], "PLUS")
    service.grant(users["expired"], "STANDARD")
    service.disable(users["blocked"])
    with service.store.transaction() as db:
        db.execute(
            "UPDATE portal_accounts SET expires_at=1 WHERE user_id=?",
            (users["expired"],),
        )
    for user in [owner, *users.values(), "unprovisioned"]:
        service.store.save_search(replace(search(), owner_id=user))
    calls = {}

    class Recorder:
        def scan(self, profile, *, network, notifications_enabled):
            calls[profile.owner_id] = (network, notifications_enabled)
            return {"search_id": profile.id, "queued": 0}

    results = scan_accounts(service, Recorder())
    assert set(calls) == {owner, users["starter"], users["paid"]}
    assert calls[users["starter"]] == (False, False)
    assert calls[users["paid"]] == (False, True)
    assert {result["user_id"] for result in results} == set(calls)


def test_real_scan_keeps_radars_private_and_sends_only_plan_allowed_alerts(portal):
    service, owner = portal
    starter = service.register("starter", "safe-member-password-123")
    paid = service.register("paid", "safe-member-password-123")
    service.grant(paid, "STANDARD")
    for user in (starter, paid):
        service.save_search(
            replace(search(notify_initial=True), owner_id=user, platforms=("OLX",))
        )

    class OfflineSource:
        configs = {"OLX": SimpleNamespace(mode="json")}

        def discover(self, platform, profile, *, network):
            assert not network
            return [offer(), *peers()]

    results = scan_accounts(service, Runner(service.store, OfflineSource()))
    queued = {result["user_id"]: result["queued"] for result in results}
    assert queued == {starter: 0, paid: 1}
    assert service.store.radar(starter)["items"]
    assert service.store.radar(paid)["items"]
    assert service.store.radar(owner)["items"] == []
    assert service.inbox(starter)["items"] == []
    assert len(service.inbox(paid)["items"]) == 1
    assert service.inbox(owner)["items"] == []
    with service.store.transaction() as db:
        db.execute("UPDATE portal_accounts SET expires_at=1 WHERE user_id=?", (paid,))
    with pytest.raises(AccessDenied):
        service.inbox(paid)


def test_demo_uses_existing_owner_without_creating_default_credentials(
    portal, tmp_path
):
    service, owner = portal
    result = create_demo(tmp_path / "demo", service.auth.path, "owner")
    assert result["FLIP_PORTAL_OWNER_ID"] == owner
    assert result["FLIP_PORTAL_PUBLIC_DATA_IS_DEMO"] == "1"
    assert Store(result["FLIP_HUNTER_DB"]).radar(owner)["items"]
    with service.auth.transaction() as db:
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 1
