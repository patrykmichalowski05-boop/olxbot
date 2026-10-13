import tempfile
import unittest

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flip_core.money import to_minor, from_minor
from flip_core.policy import (
    FlipPolicy,
    Condition,
    normalize_condition,
)
from flip_core.ledger import DealLedger
from flip_core.categories import GPUCategory, PCCategory
from flip_core.contracts import RawListing, SourceStatus


class MoneyPolicyTests(unittest.TestCase):

    def test_money(self):
        self.assertEqual(to_minor("150,55"), 15055)
        self.assertEqual(from_minor(15055), "150.55")

        for value in ("nan", "inf", -1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    to_minor(value)

    def test_policy(self):
        policy = FlipPolicy.from_legacy_settings({
            "min_profit": 400,
            "hot_profit": 700,
        })

        self.assertEqual(
            policy.decide(
                100000,
                70000,
                confidence="HIGH",
            ),
            "HOT",
        )

        self.assertEqual(
            policy.decide(
                100000,
                50000,
                confidence="HIGH",
            ),
            "BUY",
        )

        self.assertEqual(
            policy.decide(
                100000,
                90000,
                confidence="LOW",
            ),
            "REVIEW",
        )

        self.assertEqual(
            policy.decide(
                100000,
                20000,
                confidence="HIGH",
            ),
            "SKIP",
        )

        self.assertEqual(
            normalize_condition("risky"),
            Condition.RISK,
        )


class LedgerTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.db = DealLedger(
            Path(self.tmp.name) / "new_deals.db"
        )
        self.db.init_db()

    def test_transactions(self):
        result = self.db.purchase(
            "pc-serial-001",
            100000,
            key="purchase-0001",
        )

        repeated = self.db.purchase(
            "pc-serial-001",
            100000,
            key="purchase-0001",
        )

        self.assertEqual(result, repeated)

        deal_id = result["deal_id"]

        self.db.add_cost(
            deal_id,
            "PREPARATION",
            15000,
            key="cost-0000001",
        )

        self.db.sell(
            deal_id,
            180000,
            key="sale-000001",
        )

        self.assertEqual(
            self.db.get(deal_id)["realized_profit_minor"],
            65000,
        )

        self.db.add_cost(
            deal_id,
            "TRANSPORT_SALE",
            5000,
            key="cost-0000002",
        )

        self.assertEqual(
            self.db.get(deal_id)["realized_profit_minor"],
            60000,
        )

        with self.assertRaises(ValueError):
            self.db.sell(
                deal_id,
                180000,
                key="sale-000002",
            )

        with self.assertRaises(ValueError):
            self.db.purchase(
                "pc-serial-001",
                100000,
                key="purchase-0002",
            )

        with self.assertRaises(ValueError):
            self.db.purchase(
                "pc-serial-001",
                200000,
                key="purchase-0001",
            )

        with self.db.connect() as conn:
            count = conn.execute("""
                SELECT COUNT(*)
                FROM notification_outbox
            """).fetchone()[0]

        self.assertEqual(count, 2)

    def test_concurrency(self):
        with self.assertRaises(ValueError):
            self.db.purchase(
                "pc-bad",
                -1,
                key="purchase-bad1",
            )

        def purchase(_):
            return self.db.purchase(
                "pc-single",
                120000,
                key="purchase-same1",
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(purchase, range(12))
            )

        unique = {
            item["deal_id"]
            for item in results
        }

        self.assertEqual(len(unique), 1)

        with self.db.connect() as conn:
            count = conn.execute("""
                SELECT COUNT(*) FROM deals
            """).fetchone()[0]

        self.assertEqual(count, 1)


class CategoryTests(unittest.TestCase):

    def listing(self, title):
        return RawListing(
            platform="facebook",
            external_id="123",
            canonical_url="https://example.test",
            title=title,
            description="",
            price_minor=100000,
            currency="PLN",
            status=SourceStatus.UNKNOWN,
            fetched_at="2026-10-13",
            parser_version="v1",
        )

    def test_gpu(self):
        engine = GPUCategory()

        a = engine.extract_attributes(
            self.listing("RTX 5060 Ti 16GB GDDR7")
        )

        b = engine.extract_attributes(
            self.listing("RTX 5060 Ti 8GB GDDR7")
        )

        self.assertNotEqual(
            engine.comparable_key(a),
            engine.comparable_key(b),
        )

        plain = engine.extract_attributes(
            self.listing("RTX 5060 Ti 16GB")
        )

        self.assertEqual(
            engine.comparable_key(a),
            engine.comparable_key(plain),
        )

        missing = engine.extract_attributes(
            self.listing("RTX 5060 Ti")
        )

        self.assertIsNone(
            engine.comparable_key(missing)
        )

    def test_pc(self):
        engine = PCCategory()

        attributes = engine.extract_attributes(
            self.listing("Gaming PC")
        )

        self.assertIsNone(
            engine.comparable_key(attributes)
        )

        self.assertEqual(
            engine.comparable_key({
                "cpu": "R5 5600",
                "gpu": "RTX3070",
                "ram_gb": 16,
            }),
            "PC:R5 5600:RTX3070:16",
        )


if __name__ == "__main__":
    unittest.main()
