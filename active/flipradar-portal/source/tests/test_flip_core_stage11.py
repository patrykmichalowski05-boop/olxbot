import sqlite3
import tempfile
import unittest

from pathlib import Path

from flip_core.facebook_quality_audit import (
    _fb_url,
    inspect,
)


class QualityAuditTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        root = Path(temp.name)

        self.face = root / "facebook.db"
        self.alerts = root / "alerts.db"

        with sqlite3.connect(self.face) as db:
            db.execute("""
                CREATE TABLE facebook_offers (
                    listing_id TEXT PRIMARY KEY,
                    url TEXT,
                    title TEXT,
                    price INTEGER,
                    analyzed INTEGER,
                    alert_sent INTEGER,
                    last_profit REAL,
                    seen_count INTEGER,
                    last_seen TEXT
                )
            """)

        with sqlite3.connect(self.alerts) as db:
            db.execute("""
                CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY,
                    url TEXT
                )
            """)

    def add(
        self,
        ident,
        title="PC gaming",
        analyzed=1,
        alert=0,
        profit=None,
    ):
        url = (
            "https://www.facebook.com/"
            f"marketplace/item/{ident}"
        )

        with sqlite3.connect(self.face) as db:
            db.execute("""
                INSERT INTO facebook_offers
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                str(ident),
                url,
                title,
                1000,
                analyzed,
                alert,
                profit,
                2,
                "2026-10-13T12:00:00+00:00",
            ))

        return url

    def test_no_alert_not_failure_proof(self):
        self.add(1)

        result = inspect(
            self.face,
            self.alerts,
        )

        self.assertEqual(
            result["facebook"]["analyzed_flag"],
            1,
        )

        self.assertEqual(
            result["facebook"]["marked_alert_sent"],
            0,
        )

        self.assertFalse(
            result["telegram_delivery_proved"]
        )

    def test_alert_history(self):
        url = self.add(
            2,
            alert=1,
            profit=500,
        )

        with sqlite3.connect(self.alerts) as db:
            db.execute(
                "INSERT INTO alerts VALUES(1,?)",
                (url,),
            )

            db.execute(
                "INSERT INTO alerts VALUES(2,?)",
                ("https://www.olx.pl/x",),
            )

        result = inspect(
            self.face,
            self.alerts,
        )

        self.assertEqual(
            result["facebook"][
                "facebook_alerts_in_alert_history"
            ],
            1,
        )

        self.assertEqual(
            result["facebook"][
                "last_profit_ge_400_unverified"
            ],
            1,
        )

    def test_pending_unknown(self):
        self.add(
            3,
            "Okazja tylko dzisiaj",
            analyzed=0,
        )

        result = inspect(
            self.face,
            self.alerts,
            unknown_limit=1,
        )

        self.assertEqual(
            result["facebook"]["pending_flag"],
            1,
        )

        self.assertEqual(
            result["categories_from_card_titles"][
                "UNKNOWN"
            ],
            1,
        )

        self.assertEqual(
            len(result["unknown_title_samples"]),
            1,
        )

    def test_url_host(self):
        self.assertFalse(_fb_url(
            "https://facebook.com.evil.example/"
            "marketplace/item/123"
        ))

        self.assertFalse(_fb_url(
            "https://www.olx.pl/x"
        ))

        self.assertTrue(_fb_url(
            "https://m.facebook.com/"
            "marketplace/item/123?x=1"
        ))

    def test_read_only(self):
        self.add(4)

        before = (
            self.face.read_bytes(),
            self.alerts.read_bytes(),
        )

        inspect(self.face, self.alerts)

        after = (
            self.face.read_bytes(),
            self.alerts.read_bytes(),
        )

        self.assertEqual(before, after)

    def test_missing_source(self):
        with self.assertRaises(
            FileNotFoundError
        ):
            inspect(
                self.face.parent / "missing.db",
                self.alerts,
            )

    def test_missing_table(self):
        with sqlite3.connect(self.face) as db:
            db.execute(
                "DROP TABLE facebook_offers"
            )

        with self.assertRaisesRegex(
            ValueError,
            "MISSING_TABLE",
        ):
            inspect(
                self.face,
                self.alerts,
            )

    def test_limit_guard(self):
        with self.assertRaises(ValueError):
            inspect(
                self.face,
                self.alerts,
                unknown_limit=60,
            )


if __name__ == "__main__":
    unittest.main()
