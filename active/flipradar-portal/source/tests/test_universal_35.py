import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app


class Test35(unittest.TestCase):

    def test_watchlist_with_owner_token(self):
        with tempfile.TemporaryDirectory() as d:
            auth = AuthStore(
                Path(d) / 'auth.db'
            )
            auth.init_db()

            auth.create_owner(
                'watchowner',
                'strong-password-12345'
            )

            with patch.dict(
                os.environ,
                {
                    'FLIP_API_AUTH_DB': str(
                        Path(d) / 'auth.db'
                    ),
                    'FLIP_API_DATA_ROOT': d,
                    'FLIP_UNIVERSAL_DEV_DIR': d,
                }
            ):
                api = TestClient(create_app())

                login = api.post(
                    '/api/v1/auth/login',
                    json={
                        'username': 'watchowner',
                        'password': 'strong-password-12345'
                    }
                )

                self.assertEqual(
                    login.status_code,
                    200,
                    login.text
                )

                headers = {
                    'Authorization': (
                        'Bearer '
                        + login.json()['access_token']
                    )
                }

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/watchlist'
                    ).status_code,
                    401
                )

                response = api.post(
                    '/api/v1/universal/watchlist',
                    headers=headers,
                    json={
                        'key': 'MANUAL:1',
                        'label': 'GPU'
                    }
                )

                self.assertEqual(
                    response.status_code,
                    200
                )

                page = api.get(
                    '/api/v1/universal/watchlist',
                    headers=headers
                )

                self.assertEqual(
                    len(page.json()['items']),
                    1
                )

                closed = api.post(
                    '/api/v1/universal/watchlist/close',
                    headers=headers,
                    json={'key': 'MANUAL:1'}
                )

                self.assertTrue(
                    closed.json()['closed']
                )

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/watchlist',
                        headers=headers
                    ).json()['items'],
                    []
                )
