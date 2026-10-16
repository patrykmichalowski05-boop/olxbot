import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app


class Test34(unittest.TestCase):

    def test_manual_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            auth = AuthStore(root / 'auth.db')
            auth.init_db()

            auth.create_owner(
                'ownerx',
                'strong-test-pass-123'
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

                login = api.post(
                    '/api/v1/auth/login',
                    json={
                        'username': 'ownerx',
                        'password': 'strong-test-pass-123'
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

                body = {
                    'external_id': 'x1',
                    'title': 'RTX 5060 Ti 16GB',
                    'price': '1300',
                    'category': 'ELECTRONICS'
                }

                response = api.post(
                    '/api/v1/universal/manual/analyze',
                    headers=headers,
                    json=body
                )

                self.assertEqual(
                    response.status_code,
                    200,
                    response.text
                )

                self.assertEqual(
                    response.json()['decision'],
                    'NO_RELIABLE_VALUATION'
                )

                page = api.get(
                    '/api/v1/universal/radar',
                    headers=headers
                )

                self.assertEqual(
                    page.status_code,
                    200,
                    page.text
                )

                self.assertEqual(
                    len(page.json()['items']),
                    1
                )

                self.assertEqual(
                    api.post(
                        '/api/v1/universal/manual/analyze',
                        json=body
                    ).status_code,
                    401
                )
