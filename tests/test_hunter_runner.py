from dataclasses import replace
from datetime import datetime, timedelta, timezone

from examples.generate_hunter_demo import generate
from universal_v2.hunter.config import Config
from universal_v2.hunter.runner import Runner
from universal_v2.hunter.sources import SourceRegistry
from universal_v2.hunter.store import Store


def test_complete_offline_five_platform_pipeline_and_restart(tmp_path):
    config = Config.load(generate(tmp_path))
    store = Store(config.database)
    sources = SourceRegistry(config.sources, config.root)
    runner = Runner(store, sources)
    for profile in config.searches:
        store.save_search(profile)
        stats = runner.scan(profile)
        assert set(stats["sources"].values()) == {"OK"}
        assert stats["matched"] == 6
        assert stats["queued"] == 1
        assert runner.scan(profile)["queued"] == 0
    assert store.queue_summary(config.owner_id) == {"PENDING": 5}
    assert {row["platform"] for row in store.health(config.owner_id)} == {
        s.platform for s in config.sources
    }
    assert len(store.radar(config.owner_id, limit=100)["items"]) == 30
    sources.close()


def test_broken_feed_has_backoff_and_does_not_bootstrap(tmp_path):
    config = Config.load(generate(tmp_path))
    store = Store(config.database)
    profile = replace(config.searches[0], platforms=("OLX",), notify_initial=False)
    store.save_search(profile)
    (tmp_path / "olx.json").write_text("not json")
    registry = SourceRegistry(config.sources, config.root)
    runner = Runner(store, registry)
    now = datetime.now(timezone.utc)
    assert runner.scan(profile, now=now.isoformat())["sources"]["OLX"] == "INVALID_FEED"
    health = store.health(config.owner_id)[0]
    assert not health["bootstrapped"]
    assert (
        runner.scan(profile, now=(now + timedelta(seconds=1)).isoformat())["sources"][
            "OLX"
        ]
        == "BACKOFF"
    )
    generate(tmp_path)
    stats = runner.scan(profile, now=(now + timedelta(minutes=2)).isoformat())
    assert stats["sources"]["OLX"] == "OK"
    assert stats["queued"] == 0
    registry.close()
