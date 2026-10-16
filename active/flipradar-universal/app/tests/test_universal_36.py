import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app


class Test36(unittest.TestCase):

    def test_full_mobile_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            auth = AuthStore(
                root / 'auth.db'
            )
            auth.init_db()

            auth.create_owner(
                'testuser',
                'really-strong-password-123'
            )

            env = {
                'FLIP_API_AUTH_DB': str(
                    root / 'auth.db'
                ),
                'FLIP_API_DATA_ROOT': d,
                'FLIP_UNIVERSAL_DEV_DIR': d,
                'FLIP_UNIVERSAL_ENABLE_MANUAL': '1',
            }

            with patch.dict(os.environ, env):
                api = TestClient(create_app())

                self.assertEqual(
                    api.get(
                        '/api/v1/me'
                    ).status_code,
                    401
                )

                login = api.post(
                    '/api/v1/auth/login',
                    json={
                        'username': 'testuser',
                        'password': 'really-strong-password-123'
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
                        '/api/v1/me',
                        headers=headers
                    ).status_code,
                    200
                )

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/status',
                        headers=headers
                    ).status_code,
                    200
                )

                analyzed = api.post(
                    '/api/v1/universal/manual/analyze',
                    headers=headers,
                    json={
                        'external_id': 'gpu-001',
                        'title': 'RTX 5060 Ti 16GB',
                        'price': '1100',
                        'price_kind': 'FULL'
                    }
                )

                self.assertEqual(
                    analyzed.status_code,
                    200,
                    analyzed.text
                )

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/radar',
                        headers=headers
                    ).status_code,
                    200
                )

                watched = api.post(
                    '/api/v1/universal/watchlist',
                    headers=headers,
                    json={
                        'key': 'gpu-001',
                        'label': 'GPU okazja?'
                    }
                )

                self.assertEqual(
                    watched.status_code,
                    200
                )

                self.assertEqual(
                    len(
                        api.get(
                            '/api/v1/universal/watchlist',
                            headers=headers
                        ).json()['items']
                    ),
                    1
                )

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/watchlist'
                    ).status_code,
                    401
                )

                self.assertEqual(
                    api.post(
                        '/api/v1/auth/logout',
                        headers=headers
                    ).status_code,
                    200
                )

                self.assertEqual(
                    api.get(
                        '/api/v1/universal/watchlist',
                        headers=headers
                    ).status_code,
                    401
                )
