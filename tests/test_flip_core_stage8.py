import tempfile
import unittest
import json
import sqlite3

from pathlib import Path
from types import SimpleNamespace

from flip_core.peer_market import review_offer
from flip_core.peer_shadow_audit import audit


def cat():
    return SimpleNamespace(
        category="DESKTOP_PC",
        pc_pricing_input_complete=True,
        attributes={
            "cpu": "I5-9400",
            "gpu": "RTX 2060",
            "ram_gb": 16,
        },
    )


def market(
    n=5,
    cpu="I5-9400F",
):
    rows = [
        {
            "key": (
                cpu,
                "RTX 2060",
                16,
            ),
            "canonical_id": "ID" + str(i),
            "offer_id": str(i),
            "price_minor": (
                1900 + 50 * i
            ) * 100,
        }
        for i in range(n)
    ]

    return SimpleNamespace(rows=rows)


class PeerTests(unittest.TestCase):

    def test_five_comparables_review_only(self):
        result = review_offer(
            market(),
            cat(),
            100000,
        )

        self.assertEqual(
            result["status"],
            "SCENARIO_REVIEW_ONLY",
        )

        self.assertEqual(
            result["peer_count"],
            5,
        )

        self.assertEqual(
            result["decision"],
            "REVIEW",
        )

        self.assertFalse(
            result["automatic_buy_allowed"]
        )

        self.assertEqual(
            result["confirmed_sales"],
            0,
        )

        self.assertGreater(
            result["scenario_profit_minor"],
            0,
        )

    def test_too_few(self):
        result = review_offer(
            market(2),
            cat(),
            100000,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_COMPARABLES",
        )

        self.assertIsNone(
            result["scenario_profit_minor"]
        )

    def test_self_excluded(self):
        result = review_offer(
            market(),
            cat(),
            100000,
            "https://www.olx.pl/d/oferta/pc-ID0.html",
        )

        self.assertEqual(
            result["peer_count"],
            4,
        )

    def test_wrong_gpu_not_matched(self):
        evidence = market()

        for row in evidence.rows:
            row["key"] = (
                "I5-9400F",
                "RTX 3060",
                16,
            )

        self.assertEqual(
            review_offer(
                evidence,
                cat(),
                100000,
            )["peer_count"],
            0,
        )

    def test_stronger_cpu_rejected(self):
        evidence = market(
            cpu="I7-9700"
        )

        self.assertEqual(
            review_offer(
                evidence,
                cat(),
                100000,
            )["peer_count"],
            0,
        )

    def test_removed_not_ranked(self):
        result = review_offer(
            market(),
            cat(),
            100000,
            status="REMOVED",
        )

        self.assertEqual(
            result["status"],
            "OFFER_REMOVED",
        )

    def test_invalid_price(self):
        result = review_offer(
            market(),
            cat(),
            -100,
        )

        self.assertEqual(
            result["status"],
            "INVALID_TARGET",
        )

    def test_non_pc(self):
        category = cat()
        category.category = "LAPTOP"

        result = review_offer(
            market(),
            category,
            100000,
        )

        self.assertEqual(
            result["status"],
            "NOT_ELIGIBLE",
        )

    def test_outlier_guard(self):
        evidence = market(5)

        evidence.rows[-1][
            "price_minor"
        ] = 5000000

        result = review_offer(
            evidence,
            cat(),
            100000,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_AFTER_OUTLIERS",
        )

    def test_read_only_audit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            marketdb = root / "market.db"
            shadow = root / "shadow.db"

            with sqlite3.connect(marketdb) as db:
                db.execute("""
                    CREATE TABLE market_offers (
                        offer_id TEXT,
                        title TEXT,
                        url TEXT,
                        price INTEGER,
                        cpu TEXT,
                        gpu TEXT,
                        ram INTEGER,
                        last_seen TEXT,
                        active INTEGER
                    )
                """)

            with sqlite3.connect(shadow) as db:
                db.execute("""
                    CREATE TABLE listing_observations(
                        id INTEGER,
                        payload_json TEXT
                    )
                """)

                payload = {
                    "platform": "OLX",
                    "external_id": "TARGET",
                    "canonical_url": (
                        "https://www.olx.pl/d/oferta/"
                        "a-IDTARGET.html"
                    ),
                    "title": (
                        "Komputer stacjonarny i5-9400 "
                        "RTX 2060 16GB RAM"
                    ),
                    "description": "",
                    "price_minor": 90000,
                    "currency": "PLN",
                    "status": "UNKNOWN",
                    "attributes": {},
                }

                db.execute("""
                    INSERT INTO listing_observations
                    VALUES(1,?)
                """, (
                    json.dumps(payload),
                ))

            before = marketdb.read_bytes()

            result = audit(
                shadow,
                marketdb,
            )

            self.assertEqual(
                result["results"],
                {
                    "INSUFFICIENT_COMPARABLES": 1
                },
            )

            self.assertEqual(
                marketdb.read_bytes(),
                before,
            )

            self.assertFalse(
                result[
                    "automatic_buy_allowed"
                ]
            )
