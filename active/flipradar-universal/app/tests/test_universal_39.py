import unittest
from pathlib import Path


class Test39(unittest.TestCase):

    def test_client_routes(self):
        universal = Path(
            "mobile/src/api/endpoints/universal.ts"
        ).read_text(encoding="utf-8")

        client = Path(
            "mobile/src/api/client.ts"
        ).read_text(encoding="utf-8")

        for route in (
            "/api/v1/universal/watchlist",
            "/api/v1/universal/watchlist/close",
            "/api/v1/universal/manual/analyze",
        ):
            self.assertIn(route, universal)

        self.assertIn("apiRequest", universal)
        self.assertIn("Authorization", client)
        self.assertIn("refreshAccessToken", client)
