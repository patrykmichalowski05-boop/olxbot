import tempfile
import unittest
from pathlib import Path
import database as db


class RepeatAnalysisTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_db = db.DB_FILE
        db.DB_FILE = str(Path(self.tmp.name) / "test.db")
        db.init_db()
        self.id = "TEST_REPEATS"
        self.url = "https://www.olx.pl/test"

    def tearDown(self):
        db.DB_FILE = self.previous_db
        self.tmp.cleanup()

    def observe(self, price):
        return db.observe_offer(
            self.id, "Ryzen 5 3600 RTX 3060",
            price, self.url
        )

    def test_null_price_deduplication(self):
        self.assertTrue(self.observe(None)["should_analyze"])
        db.mark_analyzed(self.id, None)

        for _ in range(100):
            self.assertFalse(
                self.observe(None)["should_analyze"]
            )

    def test_price_resolved_and_drop(self):
        self.observe(None)
        db.mark_analyzed(self.id, None)

        result = self.observe(2800)
        self.assertEqual(result["reason"], "PRICE_RESOLVED")

        db.mark_analyzed(self.id, None)
        self.assertEqual(
            db.get_offer(self.id)["last_analyzed_price"], 2800
        )

        self.assertFalse(self.observe(2800)["should_analyze"])

        result = self.observe(2500)
        self.assertEqual(result["reason"], "PRICE_DROP")

        db.mark_analyzed(self.id, 2500)
        self.assertFalse(self.observe(2500)["should_analyze"])


if __name__ == "__main__":
    unittest.main()
