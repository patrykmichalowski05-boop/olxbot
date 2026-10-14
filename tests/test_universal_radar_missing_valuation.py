import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app
from universal_v2.radar_service import RadarService


class RadarWithoutValuationTest(unittest.TestCase):

    def test_manual_offer_visible_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth = AuthStore(root / "auth.sqlite")
            auth.init_db()
            auth.create_owner(
                "testowner",
                "safe-test-password-123",
            )

            env = {
                "FLIP_API_AUTH_DB": str(root / "auth.sqlite"),
                "FLIP_API_DATA_ROOT": directory,
                "FLIP_UNIVERSAL_DEV_DIR": directory,
                "FLIP_UNIVERSAL_ENABLE_MANUAL": "1",
            }

            with patch.dict(os.environ, env):
                client = TestClient(create_app())

                login = client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "testowner",
                        "password": "safe-test-password-123",
                    },
                )
                self.assertEqual(login.status_code, 200)

                token = login.json()["access_token"]
                headers = {
                    "Authorization": "Bearer " + token
                }

                # Dwie oferty z niepelna specyfikacja PC.
                for number, title in (
                    ("R-001", "Komputer RTX 3070"),
                    ("R-002", "Komputer RTX 3060"),
                ):
                    response = client.post(
                        "/api/v1/universal/manual/analyze",
                        json={
                            "external_id": number,
                            "title": title,
                            "price": "1000",
                            "category": "ELECTRONICS",
                        },
                        headers=headers,
                    )

                    self.assertEqual(
                        response.status_code,
                        200,
                        response.text,
                    )
                    self.assertEqual(
                        response.json()["decision"],
                        "NO_RELIABLE_VALUATION",
                    )

                # Strona pierwsza.
                radar = client.get(
                    "/api/v1/universal/mobile-radar",
                    params={"limit": 1},
                    headers=headers,
                )
                self.assertEqual(radar.status_code, 200)

                first = radar.json()
                self.assertEqual(len(first["items"]), 1)
                self.assertEqual(
                    first["items"][0]["decision"],
                    "NO_RELIABLE_VALUATION",
                )
                self.assertEqual(
                    first["items"][0]["price_minor"],
                    100000,
                )

                # Strona druga.
                next_page = client.get(
                    "/api/v1/universal/mobile-radar",
                    params={
                        "limit": 1,
                        "before_id": first["next_before_id"],
                    },
                    headers=headers,
                )
                self.assertEqual(
                    next_page.status_code,
                    200,
                )
                self.assertEqual(
                    len(next_page.json()["items"]),
                    1,
                )

                # Wyszukiwanie po tytule.
                search = client.get(
                    "/api/v1/universal/mobile-radar",
                    params={"q": "RTX 3070"},
                    headers=headers,
                )
                self.assertEqual(
                    len(search.json()["items"]),
                    1,
                )

                # Inny uzytkownik nie widzi tych danych.
                other = RadarService(
                    root / "observations.sqlite"
                ).page("different-user")
                self.assertEqual(other["items"], [])

                # Bez tokenu dostep jest zabroniony.
                denied = client.get(
                    "/api/v1/universal/mobile-radar"
                )
                self.assertEqual(
                    denied.status_code,
                    401,
                )
