import json
import sqlite3
import tempfile
import unittest

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from flip_core.market_evidence import (
    MarketEvidence,
    hardware_key,
    normalize_cpu,
    normalize_gpu,
)

from flip_core.market_shadow_audit import audit


@dataclass
class Category:
    category: str = "DESKTOP_PC"
    pc_pricing_input_complete: bool = True
    attributes: dict = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {
                "cpu": "I5-9400",
                "gpu": "RTX 2060",
                "ram_gb": 16,
            }


class MarketTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.market = self.root / "market.db"

        with sqlite3.connect(self.market) as db:
            db.execute("""
                CREATE TABLE market_offers (
                    offer_id TEXT PRIMARY KEY,
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

        self.today = datetime.now().isoformat(
            timespec="seconds"
        )

    def add(
        self,
        ident,
        price=2000,
        cpu="i5-9400",
        gpu="RTX 2060",
        ram=16,
        active=1,
        last_seen=None,
        title="Komputer gaming",
    ):
        with sqlite3.connect(self.market) as db:
            db.execute("""
                INSERT INTO market_offers
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                str(ident),
                title,
                (
                    "https://www.olx.pl/"
                    f"d/oferta/pc-ID{ident}.html"
                ),
                price,
                cpu,
                gpu,
                ram,
                last_seen or self.today,
                active,
            ))

    def evidence(self):
        return MarketEvidence(
            self.market
        )

    def test_normalization(self):
        self.assertEqual(
            normalize_cpu(
                "Intel Core i5 9400"
            ),
            "I5-9400",
        )

        self.assertEqual(
            normalize_cpu(
                "Ryzen 5 5600X"
            ),
            "RYZEN 5 5600X",
        )

        self.assertEqual(
            normalize_gpu(
                "GeForce RTX3060Ti"
            ),
            "RTX 3060 TI",
        )

        self.assertEqual(
            hardware_key(
                "i5-9400",
                "RTX 2060",
                "16",
            ),
            (
                "I5-9400",
                "RTX 2060",
                16,
            ),
        )

    def test_no_samples(self):
        result = self.evidence().estimate(
            Category(),
            target_price_minor=80000,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_DATA",
        )

        self.assertFalse(
            result["automatic_buy_allowed"]
        )

        self.assertIsNone(
            result["illustrative_profit_minor"]
        )

    def test_exact_only_and_asking(self):
        for i, price in enumerate((
            1800,
            1900,
            2000,
            2100,
            2200,
        ), 1):
            self.add(i, price)

        result = self.evidence().estimate(
            Category(),
            target_price_minor=100000,
        )

        self.assertEqual(
            result["status"],
            "SCENARIO_ONLY",
        )

        self.assertEqual(
            result["comparable_count"],
            5,
        )

        self.assertEqual(
            result["asking_p25_minor"],
            190000,
        )

        self.assertEqual(
            result["illustrative_resale_minor"],
            171000,
        )

        self.assertEqual(
            result["illustrative_profit_minor"],
            61000,
        )

        self.assertEqual(
            result["decision"],
            "REVIEW",
        )

        self.assertEqual(
            result["confirmed_sales"],
            0,
        )

    def test_self_exclusion(self):
        for i in range(1, 6):
            self.add(i)

        result = self.evidence().estimate(
            Category(),
            target_price_minor=100000,
            target_url=(
                "https://www.olx.pl/d/"
                "oferta/pc-ID1.html?utm=test"
            ),
        )

        self.assertEqual(
            result["comparable_count"],
            4,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_DATA",
        )

    def test_inactive_and_stale_rejected(self):
        self.add(
            1,
            active=0,
        )

        self.add(
            2,
            last_seen=(
                datetime.now()
                - timedelta(days=60)
            ).isoformat(),
        )

        self.assertEqual(
            len(self.evidence().rows),
            0,
        )

    def test_wrong_gpu_no_match(self):
        for i in range(1, 7):
            self.add(
                i,
                gpu="RTX 3060",
            )

        result = self.evidence().estimate(
            Category(),
            target_price_minor=50000,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_DATA",
        )

    def test_laptop_rejected_even_with_specs(self):
        self.add(
            1,
            title=(
                "Laptop gaming i5-9400 "
                "RTX 2060 16GB RAM"
            ),
        )

        result = self.evidence()

        self.assertEqual(
            len(result.rows),
            0,
        )

        self.assertEqual(
            result.rejections.get(
                "POSSIBLE_LAPTOP"
            ),
            1,
        )

    def test_conflicting_title_and_structured_specs(self):
        self.add(
            1,
            title=(
                "PC gaming i7-9700 "
                "RTX 3070 16GB RAM"
            ),
        )

        result = self.evidence()

        self.assertEqual(
            len(result.rows),
            0,
        )

        self.assertEqual(
            result.rejections.get(
                "SPECS_TITLE_MISMATCH"
            ),
            1,
        )

    def test_bad_offer_filters(self):
        self.add(
            1,
            price=999999,
        )

        self.add(
            2,
            title="Komputer uszkodzony",
        )

        self.add(
            3,
            cpu="",
        )

        result = self.evidence()

        self.assertEqual(
            len(result.rows),
            0,
        )

        self.assertIn(
            "BAD_PRICE",
            result.rejections,
        )

        self.assertIn(
            "INCOMPLETE_SPECS",
            result.rejections,
        )

    def test_not_pc(self):
        for i in range(1, 8):
            self.add(i)

        for category in (
            "LAPTOP",
            "GPU",
            "SMARTPHONE",
            "UNKNOWN",
        ):
            result = self.evidence().estimate(
                Category(category=category),
                target_price_minor=100000,
            )

            self.assertEqual(
                result["status"],
                "NOT_ELIGIBLE",
            )

            self.assertFalse(
                result["automatic_buy_allowed"]
            )

    def test_outlier_not_raise_quartile(self):
        for i, price in enumerate((
            1700,
            1800,
            1900,
            2000,
            2100,
            9999,
        ), 1):
            self.add(i, price)

        result = self.evidence().estimate(
            Category(),
            target_price_minor=90000,
        )

        self.assertEqual(
            result["status"],
            "SCENARIO_ONLY",
        )

        self.assertEqual(
            result["comparable_count"],
            5,
        )

        self.assertLess(
            result["asking_p25_minor"],
            200000,
        )

    def test_read_only(self):
        for i in range(1, 6):
            self.add(i)

        before = self.market.read_bytes()

        self.evidence().estimate(
            Category(),
            target_price_minor=80000,
        )

        self.assertEqual(
            before,
            self.market.read_bytes(),
        )

    def test_shadow_audit(self):
        for i in range(1, 6):
            self.add(i)

        shadow = self.root / "shadow.db"

        with sqlite3.connect(shadow) as db:
            db.execute("""
                CREATE TABLE listing_observations (
                    id INTEGER PRIMARY KEY,
                    payload_json TEXT
                )
            """)

            payload = {
                "platform": "OLX",
                "external_id": "TARGET",
                "canonical_url": (
                    "https://www.olx.pl/d/"
                    "oferta/pc-IDTARGET.html"
                ),
                "title": (
                    "Komputer stacjonarny "
                    "i5-9400 RTX 2060 16GB RAM"
                ),
                "description": "",
                "price_minor": 90000,
                "currency": "PLN",
                "status": "UNKNOWN",
                "attributes": {},
            }

            db.execute("""
                INSERT INTO listing_observations
                VALUES (1, ?)
            """, (
                json.dumps(payload),
            ))

        output = audit(
            shadow,
            self.market,
        )

        self.assertEqual(
            output["observations"],
            1,
        )

        self.assertEqual(
            output["results"],
            {"SCENARIO_ONLY": 1},
        )

        self.assertTrue(
            output[
                "no_automatic_buy_or_telegram"
            ]
        )


if __name__ == "__main__":
    unittest.main()
