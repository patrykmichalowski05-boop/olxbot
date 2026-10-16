import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from test_hunter_pricing import offer, peers, search

from universal_v2.hunter.notify import DeliveryError, Telegram, dispatch, message, money
from universal_v2.hunter.pricing import evaluate
from universal_v2.hunter.store import Store


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "hunter.sqlite3")
    profile = search(notify_initial=True)
    store.save_search(profile)
    candidate = offer()
    store.observe(profile.owner_id, [candidate])
    return store, profile, candidate, evaluate(candidate, profile, peers())


def test_record_and_alert_are_atomic(setup):
    store, profile, candidate, result = setup
    with store.transaction() as db:
        db.execute(
            "CREATE TRIGGER reject_alert BEFORE INSERT ON hunter_outbox BEGIN SELECT RAISE(ABORT,'simulated storage failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.record(profile, candidate, result, initial=False)
    assert store.radar(profile.owner_id)["items"] == []
    assert store.queue_summary(profile.owner_id) == {}
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM hunter_matches").fetchone()[0] == 0


def test_restart_duplicates_and_only_lower_price_alerts(setup):
    store, profile, candidate, result = setup
    assert store.record(profile, candidate, result, initial=False)
    restarted = Store(store.path)
    assert not restarted.record(profile, candidate, result, initial=False)
    cheaper = replace(candidate, price_minor=candidate.price_minor - 100)
    restarted.observe(profile.owner_id, [cheaper])
    assert restarted.record(
        profile, cheaper, evaluate(cheaper, profile, peers()), initial=False
    )
    alert = restarted.claim(profile.owner_id)
    assert alert["price_minor"] == cheaper.price_minor
    assert restarted.finish(alert)
    assert restarted.queue_summary(profile.owner_id) == {"CANCELLED": 1, "DONE": 1}


def test_initial_scan_is_quiet_but_new_and_cheaper_items_alert(setup):
    store, profile, candidate, result = setup
    profile = replace(profile, notify_initial=False)
    store.save_search(profile)
    assert not store.record(profile, candidate, result, initial=True)
    assert not store.record(profile, candidate, result, initial=False)
    cheaper = replace(candidate, price_minor=50000)
    store.observe(profile.owner_id, [cheaper])
    assert store.record(
        profile, cheaper, evaluate(cheaper, profile, peers()), initial=False
    )
    new = offer("brand-new")
    store.observe(profile.owner_id, [new])
    assert store.record(profile, new, evaluate(new, profile, peers()), initial=False)


def test_two_workers_and_expired_lease_cannot_ack(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(2) as pool:
        claims = list(
            pool.map(
                lambda _: store.claim(
                    profile.owner_id, now.isoformat(), lease_seconds=5
                ),
                range(2),
            )
        )
    assert sum(row is not None for row in claims) == 1
    first = next(row for row in claims if row)
    later = (now + timedelta(seconds=6)).isoformat()
    assert not store.finish(first, now=later)
    second = store.claim(profile.owner_id, later)
    assert second["lease_token"] != first["lease_token"]
    assert not store.finish(first, now=later)
    assert store.finish(second, now=later)


def test_removed_or_disabled_search_cancels_alert(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    store.save_search(replace(profile, enabled=False))
    assert store.claim(profile.owner_id) is None
    assert store.radar(profile.owner_id)["items"] == []


def test_updated_offer_does_not_inherit_stale_profit(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    expensive = replace(candidate, price_minor=999999)
    store.observe(profile.owner_id, [expensive])
    item = store.radar(profile.owner_id)["items"][0]
    assert item["valuation"]["profit"] is None
    assert item["decision"] == "NO_RELIABLE_VALUATION"
    assert store.claim(profile.owner_id) is None


def test_rename_and_pause_preserve_source_baseline(setup):
    store, profile, candidate, result = setup
    store.source_status(profile, "OLX", "OK", "loaded", mode="json")
    store.record(profile, candidate, result, initial=False)
    store.save_search(replace(profile, name="Inna nazwa", enabled=False))
    assert store.health(profile.owner_id)[0]["bootstrapped"] == 1
    store.save_search(replace(profile, name="Inna nazwa", enabled=True))
    assert len(store.radar(profile.owner_id)["items"]) == 1


def test_old_observation_does_not_overwrite_new_price(setup):
    store, profile, candidate, _ = setup
    old = replace(
        candidate,
        price_minor=1,
        observed_at=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    )
    store.observe(profile.owner_id, [old])
    assert store.offers(profile.owner_id)[0].price_minor == candidate.price_minor


def test_owner_scope_and_latest_only_pagination(setup):
    store, profile, candidate, result = setup
    for i in range(3):
        row = offer(str(i))
        store.observe(profile.owner_id, [row])
        store.record(profile, row, result, initial=False)
    store.record(
        profile,
        candidate,
        {**result, "insight": "Zaktualizowana wycena"},
        initial=False,
    )
    page = store.radar(profile.owner_id, limit=2)
    next_page = store.radar(profile.owner_id, limit=2, before_id=page["next_before_id"])
    assert len(page["items"]) == 2 and len(next_page["items"]) == 1
    assert len({row["url"] for row in page["items"] + next_page["items"]}) == 3
    assert store.radar("other-owner")["items"] == []
    assert store.detail("other-owner", page["items"][0]["snapshot_id"]) is None
    assert store.radar(profile.owner_id, query="' OR 1=1 --")["items"] == []


def test_other_database_is_not_modified(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE listings (id INTEGER)")
    with pytest.raises(ValueError, match="osobny plik"):
        Store(path)
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == [("listings",)]


def test_message_escapes_untrusted_titles_and_keeps_costs(setup):
    _, profile, candidate, result = setup
    candidate = replace(candidate, title="<b>RTX 4070</b> & deal")
    text = message(
        {"offer": candidate.payload(), "result": result, "search_name": "<script>"}
    )
    assert "&lt;script&gt;" in text and "&lt;b&gt;" in text and "&amp;" in text
    assert "przed podatkiem" in text
    assert money(123456789) == "1 234 567,89 zł"


class FakeSender:
    configured = True

    def __init__(self, error=None):
        self.error, self.sent = error, []

    def send(self, payload):
        if self.error:
            raise self.error
        self.sent.append(payload)


def test_retry_persists_and_no_credentials_does_not_consume_queue(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    sender = FakeSender(DeliveryError("TELEGRAM_RATE_LIMITED", retry_after=120))
    assert dispatch(store, profile.owner_id, sender)["retry"] == 1
    assert store.claim(profile.owner_id) is None
    assert Store(store.path).queue_summary(profile.owner_id) == {"RETRY": 1}


def test_rate_limit_applies_to_new_alerts_too(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    dispatch(
        store,
        profile.owner_id,
        FakeSender(DeliveryError("TELEGRAM_RATE_LIMITED", retry_after=900)),
    )
    new = offer("new")
    store.observe(profile.owner_id, [new])
    store.record(profile, new, evaluate(new, profile, peers()), initial=False)
    assert Store(store.path).claim(profile.owner_id) is None


def test_failed_delivery_can_be_explicitly_requeued(setup):
    store, profile, candidate, result = setup
    store.record(profile, candidate, result, initial=False)
    dispatch(
        store, profile.owner_id, FakeSender(DeliveryError("TELEGRAM_REJECTED", False))
    )
    assert store.queue_summary(profile.owner_id) == {"FAILED": 1}
    assert store.retry_failed("other-owner") == 0
    assert store.retry_failed(profile.owner_id) == 1
    assert dispatch(store, profile.owner_id, FakeSender())["sent"] == 1


def test_telegram_never_exposes_token_in_transport_exception(monkeypatch, setup):
    import requests

    monkeypatch.setenv("TEST_TOKEN", "secret-token")
    monkeypatch.setenv("TEST_CHAT", "123")

    class Broken:
        def post(self, *args, **kwargs):
            raise requests.ConnectionError(
                "https://api.telegram.org/botsecret-token/sendMessage"
            )

    sender = Telegram("TEST_TOKEN", "TEST_CHAT", Broken())
    _, profile, candidate, result = setup
    with pytest.raises(DeliveryError) as caught:
        sender.send(
            {
                "offer": candidate.payload(),
                "result": result,
                "search_name": profile.name,
            }
        )
    assert "secret-token" not in str(caught.value)
