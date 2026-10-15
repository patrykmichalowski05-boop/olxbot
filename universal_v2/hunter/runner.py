from __future__ import annotations

from datetime import timedelta

from .matching import comparable_key, matches
from .models import Search, now_iso, timestamp
from .parsers import SourceError
from .pricing import evaluate
from .sources import SourceRegistry
from .store import Store


class Runner:
    def __init__(self, store: Store, sources: SourceRegistry):
        self.store, self.sources = store, sources

    def scan(
        self, search: Search, network: bool = False, now: str | None = None
    ) -> dict:
        now = now or now_iso()
        stats = {
            "search_id": search.id,
            "fetched": 0,
            "matched": 0,
            "qualified": 0,
            "queued": 0,
            "sources": {},
        }
        if not search.enabled:
            return stats
        previous = {
            row["platform"]: row
            for row in self.store.health(search.owner_id, search.id)
        }
        fetched, successes = {}, []
        for platform in search.platforms:
            config = self.sources.configs.get(platform)
            mode = config.mode if config else "UNKNOWN"
            old = previous.get(platform, {})
            if old.get("next_due") and timestamp(old["next_due"]) > timestamp(now):
                stats["sources"][platform] = "BACKOFF"
                continue
            try:
                offers = self.sources.discover(platform, search, network=network)
            except SourceError as error:
                self.store.source_status(
                    search,
                    platform,
                    error.code,
                    str(error),
                    retry_after=error.retry_after,
                    now=now,
                    mode=mode,
                )
                stats["sources"][platform] = error.code
            else:
                fetched[platform] = offers
                successes.append(platform)
                self.store.observe(search.owner_id, offers)
                stats["fetched"] += len(offers)
                stats["sources"][platform] = "OK"
        peers = self.store.offers(
            search.owner_id,
            (timestamp(now) - timedelta(days=search.reference_days)).isoformat(),
        )
        groups = {}
        latest = {peer.key: peer for peer in peers}
        for peer in peers:
            key = comparable_key(peer, search)
            if key:
                groups.setdefault(key, []).append(peer)
        for platform, offers in fetched.items():
            for offer in offers:
                current = latest.get(offer.key)
                if current is None or timestamp(offer.observed_at) < timestamp(
                    current.observed_at
                ):
                    continue
                if not matches(offer, search):
                    continue
                stats["matched"] += 1
                result = evaluate(
                    offer,
                    search,
                    groups.get(comparable_key(offer, search), []),
                    timestamp(now),
                )
                stats["qualified"] += int(result["qualifies"])
                stats["queued"] += self.store.record(
                    search,
                    offer,
                    result,
                    initial=not previous.get(platform, {}).get("bootstrapped", False),
                    now=now,
                )
        # A failed or interrupted scan never advances that source's baseline.
        for platform in successes:
            config = self.sources.configs.get(platform)
            self.store.source_status(
                search,
                platform,
                "OK",
                "Oferty zostały sprawdzone",
                len(fetched[platform]),
                now=now,
                mode=config.mode if config else "UNKNOWN",
            )
        return stats
