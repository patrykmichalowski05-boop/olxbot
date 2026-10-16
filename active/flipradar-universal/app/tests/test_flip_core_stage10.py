import json
import sqlite3
import tempfile
import unittest

from datetime import datetime, timezone, timedelta
from pathlib import Path

from flip_core.unified_shadow import (
    audit, convert, freshness,
)


def payload(source, ident, **kwargs):
    result = {
        "platform": source,
        "external_id": ident,
        "title": "Komputer gaming",
        "canonical_url": "https://example.com/item",
        "description": "",
        "currency": "PLN" if source == "OLX" else "UNKNOWN",
        "price_minor": 100000 if source == "OLX" else None,
        "status": "UNKNOWN",
        "attributes": {},
    }
    result.update(kwargs)
    return result


def record(source, ident, **kwargs):
    return {
        "listing_key": source + ":" + ident,
        "payload_json": json.dumps(
            payload(source, ident, **kwargs)
        ),
    }


class UnifiedTests(unittest.TestCase):

    def test_recent_facebook_is_not_active_confirmation(self):
        now = datetime.now(timezone.utc)
        result = freshness(
            now.isoformat(),
            now,
        )
        self.assertEqual(
            result, "RECENTLY_OBSERVED_UNVERIFIED"
        )

    def test_old_facebook_is_stale(self):
        now = datetime.now(timezone.utc)
        result = freshness(
            (now - timedelta(days=10)).isoformat(),
            now,
        )
        self.assertEqual(result, "STALE_OBSERVATION")

    def test_missing_time(self):
        self.assertEqual(freshness(None), "UNKNOWN_TIME")

    def test_olx_does_not_infer_replay_time(self):
        result = convert(
            "OLX",
            record("OLX", "1"),
        )
        self.assertEqual(
            result["observation_freshness"],
            "UNKNOWN_TIME",
        )

    def test_fb_price_not_verified(self):
        result = convert(
            "FACEBOOK",
            record(
                "FACEBOOK", "123",
                source_evidence={
                    "last_seen": datetime.now(
                        timezone.utc
                    ).isoformat()
                },
            ),
        )
        self.assertFalse(result["auto_buy_allowed"])
        self.assertIn(
            "CURRENCY_UNVERIFIED",
            result["risk_flags"],
        )

    def test_wrong_source_rejected(self):
        with self.assertRaises(ValueError):
            convert(
                "OLX",
                record("FACEBOOK", "123"),
            )

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            convert("OLX", {
                "listing_key": "OLX:1",
                "payload_json": "{broken",
            })

    def test_both_sources_and_latest_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            olx = root / "olx.db"
            fb = root / "facebook.db"

            for path in (olx, fb):
                with sqlite3.connect(path) as db:
                    db.execute("""
                        CREATE TABLE listing_observations (
                            id INTEGER PRIMARY KEY,
                            listing_key TEXT,
                            payload_json TEXT
                        )
                    """)

            with sqlite3.connect(olx) as db:
                old = record("OLX", "100")
                new = record(
                    "OLX", "100",
                    title="Komputer stacjonarny",
                )
                db.execute(
                    "INSERT INTO listing_observations VALUES(1,?,?)",
                    (old["listing_key"], old["payload_json"]),
                )
                db.execute(
                    "INSERT INTO listing_observations VALUES(2,?,?)",
                    (new["listing_key"], new["payload_json"]),
                )

            with sqlite3.connect(fb) as db:
                item = record("FACEBOOK", "200")
                db.execute(
                    "INSERT INTO listing_observations VALUES(1,?,?)",
                    (item["listing_key"], item["payload_json"]),
                )

            result = audit(olx, fb)

            self.assertEqual(
                result["total_unique_listings"], 2
            )
            self.assertEqual(
                result["by_platform"],
                {"OLX": 1, "FACEBOOK": 1},
            )
            self.assertFalse(
                result["automatic_valuation_allowed"]
            )
            self.assertFalse(
                result["automatic_buy_allowed"]
            )


if __name__ == "__main__":
    unittest.main()
