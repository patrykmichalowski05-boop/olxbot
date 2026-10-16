import sqlite3
import tempfile
import unittest
from pathlib import Path

from flip_core.ledger import DealLedger
from flip_core.legacy_audit import audit_legacy
from flip_core.listing_repository import (
    LegacyListingReader,
    platform_from,
)
from flip_core.profit_engine import quote
from flip_core.policy import FlipPolicy


class Stage2Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_transaction_rollback(self):
        class FailingLedger(DealLedger):
            def _event(self, *args):
                raise RuntimeError("Simulated failure")

        db = FailingLedger(self.root / "deals.db")
        db.init_db()

        with self.assertRaises(RuntimeError):
            db.purchase(
                "instance-001",
                100000,
                key="purchase-fail-0001",
            )

        with db.connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM deals"
            ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_legacy_audit(self):
        with sqlite3.connect(
            self.root / "flip_results.db"
        ) as db:
            db.execute("""
                CREATE TABLE flips (
                    id INTEGER,
                    alert_id INTEGER,
                    extra_cost REAL
                )
            """)
            db.execute(
                "INSERT INTO flips VALUES (1,10,150)"
            )

        with sqlite3.connect(
            self.root / "alert_history.db"
        ) as db:
            db.execute("""
                CREATE TABLE alerts (
                    id INTEGER,
                    offer_key TEXT
                )
            """)
            db.execute(
                "INSERT INTO alerts VALUES (10,'OLX:TEST')"
            )

        with sqlite3.connect(
            self.root / "deal_crm.db"
        ) as db:
            db.execute("""
                CREATE TABLE sale_prep_costs (
                    id INTEGER,
                    offer_key TEXT,
                    cost REAL
                )
            """)
            db.execute(
                "INSERT INTO sale_prep_costs VALUES "
                "(1,'OLX:TEST',150)"
            )

        result = audit_legacy(self.root)

        self.assertEqual(
            len(result["potential_double_count"]), 1
        )
        self.assertFalse(
            result["migration_safe_automatically"]
        )

    def test_platform(self):
        self.assertEqual(
            platform_from("https://www.olx.pl/d/test"),
            "OLX",
        )
        self.assertEqual(
            platform_from(
                "https://www.facebook.com/marketplace/item/1"
            ),
            "FACEBOOK",
        )
        self.assertEqual(
            platform_from("https://example.com/test"),
            "UNKNOWN",
        )

    def test_paginated_listings(self):
        with sqlite3.connect(
            self.root / "alert_history.db"
        ) as db:
            db.execute("""
                CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY,
                    offer_key TEXT,
                    title TEXT,
                    url TEXT,
                    price REAL,
                    score INTEGER,
                    created_at TEXT
                )
            """)

            for n in range(1, 6):
                db.execute("""
                    INSERT INTO alerts VALUES (
                        ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    n,
                    f"OLX:{n}",
                    f"PC {n}",
                    f"https://www.olx.pl/oferta/{n}",
                    1000,
                    70,
                    "2026-10-13",
                ))

        reader = LegacyListingReader(self.root)

        first = reader.list(limit=2)
        second = reader.list(
            limit=2,
            before_id=first[-1]["id"],
        )

        self.assertEqual(
            [item["id"] for item in first],
            [5, 4],
        )
        self.assertEqual(
            [item["id"] for item in second],
            [3, 2],
        )
        self.assertEqual(
            reader.list(q="PC 2")[0]["id"],
            2,
        )

    def test_profit(self):
        policy = FlipPolicy(
            min_profit_minor=40000,
            hot_profit_minor=70000,
        )

        result = quote(
            150000,
            220000,
            {
                "TRANSPORT_BUY": 5000,
                "REPAIR": 10000,
                "FEE": 6000,
                "TRANSPORT_SALE": 2000,
                "RISK_RESERVE": 7000,
            },
            policy,
            confidence="HIGH",
            condition="normal",
        )

        self.assertEqual(
            result["operating_profit_minor"],
            40000,
        )
        self.assertEqual(
            result["max_purchase_minor"],
            150000,
        )
        self.assertEqual(
            result["decision"],
            "BUY",
        )

    def test_invalid_money(self):
        with self.assertRaises(ValueError):
            quote(100000, 200000, {
                "REPAIR": -100
            })

        with self.assertRaises(ValueError):
            quote(True, 200000)


if __name__ == "__main__":
    unittest.main()
