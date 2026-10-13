import os
import sqlite3
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore


TEST_PASS = "valid-test-password-123"


class MobileHTTPTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name)
        auth_path = root / "auth.db"

        auth = AuthStore(auth_path)
        auth.init_db()
        auth.create_owner(
            "testowner",
            TEST_PASS,
        )

        with sqlite3.connect(
            root / "alert_history.db"
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

            db.execute("""
                INSERT INTO alerts VALUES (
                    7,
                    'TEST:7',
                    'PC i5',
                    'https://www.olx.pl/test',
                    900,
                    80,
                    '2026-10-13'
                )
            """)

        with sqlite3.connect(
            root / "offer_snapshots.db"
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

            db.execute("""
                INSERT INTO snapshots VALUES (
                    3,
                    'TEST:7',
                    'PC i5',
                    'https://www.olx.pl/test',
                    900,
                    '{"title":"PC i5","_source":"OLX"}',
                    '{"quick_sale":1500}',
                    '{"action":"WATCH"}',
                    '2026-10-13'
                )
            """)

        with patch.dict(os.environ, {
            "FLIP_API_AUTH_DB": str(auth_path),
            "FLIP_API_DATA_ROOT": str(root),
        }):
            from flip_core.mobile_api import create_app
            self.client = TestClient(create_app())

    def test_auth_and_radar(self):
        c = self.client

        self.assertEqual(
            c.get("/api/v1/listings").status_code,
            401,
        )

        self.assertEqual(
            c.get("/api/v1/radar").status_code,
            401,
        )

        response = c.post(
            "/api/v1/auth/login",
            json={
                "username": "testowner",
                "password": TEST_PASS,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        tokens = response.json()

        headers = {
            "Authorization":
                "Bearer " + tokens["access_token"],
        }

        listing = c.get(
            "/api/v1/listings",
            headers=headers,
        )

        self.assertEqual(
            listing.status_code,
            200,
            listing.text,
        )

        self.assertEqual(
            listing.json()["items"][0]["price_minor"],
            90000,
        )

        self.assertEqual(
            c.get(
                "/api/v1/listings/7",
                headers=headers,
            ).status_code,
            200,
        )

        radar = c.get(
            "/api/v1/radar",
            headers=headers,
        )

        self.assertEqual(
            radar.status_code,
            200,
            radar.text,
        )

        self.assertEqual(
            radar.json()["items"][0]["decision"],
            "WATCH",
        )

        refresh = c.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token":
                    tokens["refresh_token"],
            },
        )

        self.assertEqual(
            refresh.status_code,
            200,
            refresh.text,
        )

        self.assertEqual(
            c.get(
                "/api/v1/me",
                headers=headers,
            ).status_code,
            401,
        )

        new_headers = {
            "Authorization":
                "Bearer " +
                refresh.json()["access_token"],
        }

        self.assertEqual(
            c.get(
                "/api/v1/me",
                headers=new_headers,
            ).status_code,
            200,
        )

        self.assertEqual(
            c.post(
                "/api/v1/auth/logout",
                headers=new_headers,
            ).status_code,
            200,
        )

        self.assertEqual(
            c.get(
                "/api/v1/me",
                headers=new_headers,
            ).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
