import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from flip_core.auth_store import AuthStore
from universal_v2.hunter.models import Search
from universal_v2.hunter.store import Store
from universal_v2.portal.store import AccessDenied, PortalStore


@pytest.fixture
def portal(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3")
    auth.init_db()
    owner = auth.create_owner("owner", "safe-owner-password-123")
    store = Store(tmp_path / "hunter.sqlite3")
    portal = PortalStore(store, auth, owner)
    member = portal.register("alice", "safe-member-password-123")
    return portal, owner, member


def profile(user, identity="test-query", query="RTX 4070"):
    return Search(identity, user, query, query, category="ELECTRONICS")


def test_existing_owner_keeps_access_and_registration_is_always_start(portal):
    service, owner, member = portal
    assert service.account(owner)["role"] == "OWNER"
    assert service.account(owner)["access"]["remaining"] is None
    account = service.account(member)
    assert account["role"] == "MEMBER" and account["plan"]["code"] == "START"
    assert account["access"]["remaining"] == 3
    assert not account["access"]["can_receive_notifications"]
    with pytest.raises(ValueError):
        service.auth.create_owner("another", "another-owner-password")


def test_first_boot_requires_an_owner_without_permanently_locking_migration(tmp_path):
    auth = AuthStore(tmp_path / "auth.sqlite3")
    auth.init_db()
    store = Store(tmp_path / "hunter.sqlite3")
    with pytest.raises(RuntimeError, match="bootstrap"):
        PortalStore(store, auth)
    owner = auth.create_owner("owner", "safe-owner-password-123")
    with pytest.raises(RuntimeError, match="OWNER_ID"):
        PortalStore(store, auth, "unknown-user")
    service = PortalStore(store, auth, owner)
    assert service.account(owner)["role"] == "OWNER"


def test_quota_search_and_updates_are_atomic_and_idempotent(portal):
    service, _, member = portal
    first = profile(member)
    service.save_search(first)
    service.save_search(first)
    service.save_search(replace(first, name="Nowa nazwa", min_profit_minor=90000))
    assert service.account(member)["access"]["remaining"] == 2
    service.save_search(replace(first, query="RTX 4060"))
    assert service.account(member)["access"]["remaining"] == 1
    service.save_search(profile(member, "third-query", "iPhone 14"))
    with pytest.raises(AccessDenied) as error:
        service.save_search(profile(member, "fourth-query"))
    assert error.value.code == "QUOTA_EXHAUSTED"
    assert len(service.store.searches(member)) == 2


def test_failed_search_write_rolls_back_usage(portal):
    service, _, member = portal
    with service.store.transaction() as db:
        db.execute(
            "CREATE TRIGGER stop_search BEFORE INSERT ON hunter_searches BEGIN SELECT RAISE(ABORT,'simulated storage failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        service.save_search(profile(member))
    assert service.account(member)["access"]["remaining"] == 3
    assert service.store.searches(member) == []


def test_concurrent_requests_cannot_overdraw_quota(portal):
    service, _, member = portal

    def create(index):
        try:
            service.save_search(profile(member, f"query-{index}"))
            return True
        except AccessDenied:
            return False

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(create, range(12)))
    assert sum(results) == 3
    assert service.account(member)["access"]["remaining"] == 0
    assert len(service.store.searches(member)) == 3


def test_plan_request_does_not_activate_or_reset_credits(portal):
    service, owner, member = portal
    service.save_search(profile(member))
    request = service.request_plan(member, "STANDARD")
    service.request_plan(member, "PLUS")
    assert service.account(member)["plan"]["code"] == "START"
    assert service.account(member)["access"]["remaining"] == 2
    assert len(service.admin_list(owner)["requests"]) == 1
    assert service.account(member)["plan_request"]["id"] == request["id"]
    assert service.account(member)["plan_request"]["plan"] == "PLUS"


def test_member_cannot_manage_plans_or_read_admin_data(portal):
    service, owner, member = portal
    with pytest.raises(AccessDenied):
        service.admin_list(member)
    with pytest.raises(AccessDenied):
        service.admin_access(member, "admin-operation-1", member, "activate", "PLUS")
    assert service.account(member)["plan"]["code"] == "START"
    with pytest.raises(ValueError):
        service.admin_access(owner, "admin-operation-2", owner, "disable")


def test_owner_activation_is_idempotent_and_expires(portal):
    service, owner, member = portal
    now = [1_800_000_000]
    service.clock = lambda: now[0]
    service.admin_access(owner, "admin-operation-1", member, "activate", "STANDARD")
    service.save_search(profile(member))
    service.admin_access(owner, "admin-operation-1", member, "activate", "STANDARD")
    assert service.account(member)["access"]["remaining"] == 19
    now[0] += 30 * 86400
    with pytest.raises(AccessDenied):
        service.require_bot(member)
    # Account and request remain available so an expired user can renew.
    assert service.account(member)["access"]["reason"] == "EXPIRED"
    assert service.request_plan(member, "PLUS")["status"] == "PENDING"


def test_guest_three_requests_cookie_reset_and_replay(portal):
    service, _, _ = portal
    cookie = None
    result, cookie = service.search(
        "RTX 4070", "operation-0", lambda _: [], guest_cookie=cookie, ip_hash="ip-a"
    )
    assert result["remaining"] == 2
    repeated, _ = service.search(
        "RTX 4070",
        "operation-0",
        lambda _: pytest.fail("should use existing response"),
        guest_cookie=cookie,
        ip_hash="ip-a",
    )
    assert repeated == result
    for i in range(1, 3):
        _, cookie = service.search(
            "RTX 4070",
            f"operation-{i}",
            lambda _: [],
            guest_cookie=cookie,
            ip_hash="ip-a",
        )
    with pytest.raises(AccessDenied):
        service.search(
            "RTX 4070", "operation-3", lambda _: [], guest_cookie=cookie, ip_hash="ip-a"
        )
    with pytest.raises(AccessDenied):
        service.search(
            "RTX 4070", "operation-4", lambda _: [], guest_cookie=None, ip_hash="ip-a"
        )


def test_unavailable_lookup_does_not_spend_credit(portal):
    service, _, member = portal

    def unavailable(_):
        raise OSError("source unavailable")

    with pytest.raises(OSError):
        service.search("RTX 4070", "lookup-operation", unavailable, user_id=member)
    assert service.account(member)["access"]["remaining"] == 3


def test_restart_does_not_promote_members_or_orphan_registration(portal):
    service, owner, member = portal
    orphan = service.auth.register_user("orphan", "safe-orphan-password-123")
    restarted = PortalStore(service.store, service.auth, owner)
    assert restarted.account(member)["plan"]["code"] == "START"
    with pytest.raises(AccessDenied):
        restarted.account(orphan)


def test_browser_tabs_and_native_refresh_logout(portal):
    service, _, member = portal
    tokens = service.auth.login("alice", "safe-member-password-123")
    cookie = service.create_browser_session(member, tokens["access_token"])
    tab1 = service.resume_browser(cookie)
    tab2 = service.resume_browser(cookie)
    assert service.auth.verify_access(tab1["access_token"]) == member
    assert service.auth.verify_access(tab2["access_token"]) == member
    native = service.auth.refresh(tokens["refresh_token"])
    service.logout_access(native["access_token"])
    for access in [native["access_token"], tab1["access_token"], tab2["access_token"]]:
        with pytest.raises(ValueError):
            service.auth.verify_access(access)
    with pytest.raises(AccessDenied):
        service.resume_browser(cookie)
