import unittest
from pathlib import Path


class Test39(unittest.TestCase):

    def test_client_routes(self):
        code = Path(
            'mobile/src/api.ts'
        ).read_text(encoding='utf-8')

        for route in (
            '/api/v1/universal/watchlist',
            '/api/v1/universal/watchlist/close',
            '/api/v1/universal/manual/analyze',
        ):
            self.assertIn(route, code)

        self.assertIn(
            'universalAuthenticatedRequest',
            code
        )
