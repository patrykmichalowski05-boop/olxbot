import sqlite3
import tempfile
import unittest

from pathlib import Path

from flip_core.facebook_cards import (
    canonical_facebook_url,
    convert_card,
    raw_card_price,
    read_cards,
)

from flip_core.facebook_shadow import ingest


class FacebookStage9Tests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.source = self.root / "facebook_seen.db"
        self.shadow = self.root / "facebook-shadow.db"

        with sqlite3.connect(self.source) as db:
            db.execute("""
                CREATE TABLE facebook_offers (
                    listing_id TEXT PRIMARY KEY,
                    url TEXT,
                    title TEXT,
                    price INTEGER,
                    last_seen TEXT,
                    analyzed INTEGER,
                    alert_sent INTEGER
                )
            """)

    def add(
        self,
        ident,
        title="Komputer gaming",
        price=900,
        url=None,
    ):
        if url is None:
            url = (
                "https://www.facebook.com/"
                f"marketplace/item/{ident}"
            )

        with sqlite3.connect(self.source) as db:
            db.execute("""
                INSERT INTO facebook_offers
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(ident),
                url,
                title,
                price,
                "2026-10-13T12:00:00",
                1,
                0,
            ))

    def test_url(self):
        result = canonical_facebook_url(
            "https://m.facebook.com/"
            "marketplace/item/123?tracking=1",
            "123",
        )

        self.assertEqual(
            result,
            "https://www.facebook.com/"
            "marketplace/item/123",
        )

    def test_invalid_domain(self):
        self.assertIsNone(
            canonical_facebook_url(
                "https://facebook.com.evil.example/"
                "marketplace/item/123",
                "123",
            )
        )

    def test_id_mismatch(self):
        self.assertIsNone(
            canonical_facebook_url(
                "https://www.facebook.com/"
                "marketplace/item/123",
                "456",
            )
        )

    def test_unknown_currency(self):
        payload, error = convert_card({
            "listing_id": "123",
            "url": (
                "https://www.facebook.com/"
                "marketplace/item/123"
            ),
            "title": (
                "PC gaming Ryzen 5 5600 "
                "RTX 3060 16GB RAM"
            ),
            "price": 1500,
            "last_seen": "2026-10-13",
        })

        self.assertIsNone(error)
        self.assertEqual(
            payload["currency"],
            "UNKNOWN",
        )
        self.assertIsNone(
            payload["price_minor"]
        )
        self.assertEqual(
            payload["status"],
            "UNKNOWN",
        )
        self.assertEqual(
            payload["classification"],
            "DESKTOP_PC",
        )

    def test_price_validation(self):
        self.assertEqual(
            raw_card_price(800),
            "800",
        )
        self.assertIsNone(
            raw_card_price(float("nan"))
        )
        self.assertIsNone(
            raw_card_price(-1)
        )
        self.assertIsNone(
            raw_card_price(True)
        )

    def test_missing_title(self):
        payload, error = convert_card({
            "listing_id": "123",
            "url": (
                "https://www.facebook.com/"
                "marketplace/item/123"
            ),
            "title": "",
            "price": 900,
        })

        self.assertIsNone(payload)
        self.assertEqual(
            error,
            "MISSING_TITLE",
        )

    def test_read_only_and_idempotent(self):
        self.add(
            123,
            "PC gaming i5-9400 RTX 2060 16GB RAM",
        )
        self.add(
            456,
            "Laptop Lenovo",
            price=None,
        )

        original = self.source.read_bytes()

        first = ingest(
            self.source,
            self.shadow,
        )

        second = ingest(
            self.source,
            self.shadow,
        )

        self.assertEqual(
            first["cards_importable"],
            2,
        )
        self.assertEqual(
            second["shadow_observations_total"],
            2,
        )
        self.assertEqual(
            self.source.read_bytes(),
            original,
        )
        self.assertFalse(
            first["automatic_valuation_allowed"]
        )

    def test_invalid_row_rejected(self):
        self.add(
            123,
            url=(
                "https://example.com/"
                "marketplace/item/123"
            ),
        )

        cards, report = read_cards(
            self.source
        )

        self.assertEqual(
            len(cards),
            0,
        )
        self.assertEqual(
            report["cards_rejected"],
            {"INVALID_URL": 1},
        )

    def test_missing_database(self):
        with self.assertRaises(
            FileNotFoundError
        ):
            read_cards(
                self.root / "missing.db"
            )


if __name__ == "__main__":
    unittest.main()
