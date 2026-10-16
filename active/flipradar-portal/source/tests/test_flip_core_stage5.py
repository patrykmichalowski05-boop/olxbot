import sqlite3
import tempfile
import unittest
from pathlib import Path

from flip_core.snapshot_bridge import (
    SnapshotBridgeError,
    normalize_snapshot,
)
from flip_core.shadow_replay import replay
from flip_core.observations import ObservationStore


def record(
    ident,
    url,
    price,
    title="Komputer",
    currency="PLN",
):
    return {
        "id": ident,
        "offer_key": f"LEGACY:{ident}",
        "url": url,
        "price": price,
        "title": title,
        "details_json":
            '{"currency":"' + currency + '"}',
        "valuation_json": '{"profit":450}',
        "action_json": '{"action":"WATCH"}',
        "score": 75,
        "mode": "LOCAL",
        "trigger": "NEW",
        "created_at": "2026-10-13",
    }


class Stage5Tests(unittest.TestCase):

    def test_olx_normalization(self):
        row = record(
            1,
            "https://www.olx.pl/d/oferta/pc-ID12345.html"
            "?utm_source=test",
            1500,
        )

        listing, payload, analysis = normalize_snapshot(row)

        self.assertEqual(listing.platform, "OLX")
        self.assertEqual(listing.external_id, "ID12345")
        self.assertEqual(listing.price_minor, 150000)
        self.assertEqual(
            listing.status.value, "UNKNOWN"
        )
        self.assertNotIn(
            "utm_source", listing.canonical_url
        )
        self.assertEqual(
            analysis["legacy_valuation"]["profit"],
            450,
        )

    def test_facebook(self):
        row = record(
            2,
            "https://www.facebook.com/marketplace/item/98765",
            800,
        )

        listing, _, _ = normalize_snapshot(row)

        self.assertEqual(listing.platform, "FACEBOOK")
        self.assertEqual(listing.external_id, "98765")
        self.assertEqual(listing.price_minor, 80000)

    def test_invalid_currency(self):
        with self.assertRaises(SnapshotBridgeError):
            normalize_snapshot(record(
                3,
                "https://www.olx.pl/d/oferta/a-ID111.html",
                900,
                currency="EUR",
            ))

    def test_invalid_url_and_price(self):
        with self.assertRaises(SnapshotBridgeError):
            normalize_snapshot(record(
                4,
                "https://olx.pl.evil.example/item",
                900,
            ))

        with self.assertRaises(SnapshotBridgeError):
            normalize_snapshot(record(
                5,
                "https://www.olx.pl/d/oferta/a-ID22.html",
                float("nan"),
            ))

    def test_replay_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "legacy.db"
            output = root / "shadow.db"

            with sqlite3.connect(source) as db:
                db.execute("""
                    CREATE TABLE snapshots (
                        id INTEGER PRIMARY KEY,
                        offer_key TEXT,
                        title TEXT,
                        url TEXT,
                        price REAL,
                        details_json TEXT,
                        valuation_json TEXT,
                        action_json TEXT,
                        score INTEGER,
                        mode TEXT,
                        trigger TEXT,
                        created_at TEXT
                    )
                """)

                base = record(
                    1,
                    "https://www.olx.pl/d/oferta/a-ID11.html",
                    1000,
                )

                fields = list(base)
                values = [base[k] for k in fields]

                marks = ",".join(
                    "?" for _ in fields
                )

                db.execute(
                    "INSERT INTO snapshots ("
                    + ",".join(fields)
                    + ") VALUES ("
                    + marks
                    + ")",
                    values,
                )

            first = replay(source, output, 50)
            second = replay(source, output, 50)

            self.assertEqual(
                first["accepted_snapshots"], 1
            )
            self.assertEqual(
                second["accepted_snapshots"], 1
            )

            with sqlite3.connect(output) as db:
                observations = db.execute(
                    "SELECT COUNT(*) FROM listing_observations"
                ).fetchone()[0]

                valuations = db.execute(
                    "SELECT COUNT(*) FROM valuation_runs"
                ).fetchone()[0]

            self.assertEqual(observations, 1)
            self.assertEqual(valuations, 1)

            self.assertEqual(
                len(ObservationStore(output).history(
                    "OLX:ID11"
                )),
                1,
            )


if __name__ == "__main__":
    unittest.main()
