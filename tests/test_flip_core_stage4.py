import os
import sqlite3
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from flip_core.auth_store import (
    AuthStore,
    LoginRateLimited,
)
from flip_core.radar_repository import SnapshotRadar


TEST_PASS = "test-only-password-123"


class Stage4Tests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_radar_without_telegram_alert(self):
        with sqlite3.connect(
            self.root / "offer_snapshots.db"
        ) as db:
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
                    created_at TEXT
                )
            """)

            rows = [
                (
                    1, "FB:1", "Stara cena",
                    "https://facebook.com/marketplace/item/1",
                    1000, "WATCH"
                ),
                (
                    2, "FB:1", "Nowa cena",
                    "https://facebook.com/marketplace/item/1",
                    800, "HOT"
                ),
                (
                    3, "OLX:2", "Oferta SKIP",
                    "https://www.olx.pl/oferta/2",
                    1200, "SKIP"
                ),
                (
                    4, "OLX:3", "Oferta WATCH",
                    "https://www.olx.pl/oferta/3",
                    600, "WATCH"
                ),
            ]

            for ident, key, title, url, price, decision in rows:
                db.execute("""
                    INSERT INTO snapshots VALUES (
                        ?, ?, ?, ?, ?,
                        '{}', '{}', ?, '2026-10-13'
                    )
                """, (
                    ident, key, title, url, price,
                    '{"action":"' + decision + '"}',
                ))

        radar = SnapshotRadar(self.root)

        first = radar.list(limit=2)
        self.assertEqual(
            [x["snapshot_id"] for x in first],
            [4, 3],
        )

        second = radar.list(
            limit=2,
            before_id=first[-1]["snapshot_id"],
        )

        self.assertEqual(
            [x["snapshot_id"] for x in second],
            [2],
        )

        self.assertEqual(
            second[0]["decision"],
            "HOT",
        )

        self.assertEqual(
            radar.list(q="Nowa")[0]["price_minor"],
            80000,
        )

    def test_login_lockout_persists(self):
        auth = AuthStore(self.root / "auth.db")
        auth.init_db()
        auth.create_owner("owner", TEST_PASS)

        for _ in range(4):
            with self.assertRaises(ValueError):
                auth.login("owner", "bad-password")

        with self.assertRaises(LoginRateLimited):
            auth.login("owner", "bad-password")

        with self.assertRaises(LoginRateLimited):
            auth.login("owner", TEST_PASS)

        with auth.transaction() as db:
            attempt = db.execute("""
                SELECT attempts, locked_until
                FROM login_attempts
                WHERE username='owner'
            """).fetchone()

        self.assertEqual(attempt["attempts"], 5)
        self.assertGreater(attempt["locked_until"], 0)

    def test_api_rate_limit_and_headers(self):
        auth_path = self.root / "auth.db"
        auth = AuthStore(auth_path)
        auth.init_db()
        auth.create_owner("owner", TEST_PASS)

        with patch.dict(os.environ, {
            "FLIP_API_AUTH_DB": str(auth_path),
            "FLIP_API_DATA_ROOT": str(self.root),
        }):
            from flip_core.mobile_api import create_app
            client = TestClient(create_app())

        response = client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("cache-control"),
            "no-store",
        )
        self.assertEqual(
            response.headers.get("x-content-type-options"),
            "nosniff",
        )

        codes = []

        for _ in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "owner",
                    "password": "wrong-password",
                },
            )
            codes.append(response.status_code)

        self.assertEqual(
            codes,
            [401, 401, 401, 401, 429],
        )

        self.assertEqual(
            client.post(
                "/api/v1/auth/login",
                json={
                    "username": "owner",
                    "password": TEST_PASS,
                },
            ).status_code,
            429,
        )

    def test_mobile_points_to_radar(self):
        root = Path(__file__).resolve().parents[1]

        api = (root / "mobile/src/api.ts").read_text(
            encoding="utf-8"
        )
        app = (root / "mobile/App.tsx").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "/api/v1/radar?limit=50",
            api,
        )
        self.assertNotIn(
            "/api/v1/listings?limit=50",
            api,
        )
        self.assertIn(
            "getRadar()",
            app,
        )
        self.assertIn(
            "item.snapshot_id",
            app,
        )


if __name__ == "__main__":
    unittest.main()
