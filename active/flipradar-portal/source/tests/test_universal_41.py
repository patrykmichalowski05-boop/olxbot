import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app


class Test41(unittest.TestCase):

    def test_new_endpoint_requires_login(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            auth = AuthStore(root / 'auth.sqlite')
            auth.init_db()
            auth.create_owner(
                'testowner',
                'safe-test-password-123'
            )

            env = {
                'FLIP_API_AUTH_DB': str(
                    root / 'auth.sqlite'
                ),
                'FLIP_API_DATA_ROOT': d,
                'FLIP_UNIVERSAL_DEV_DIR': d,
            }

            with patch.dict(os.environ, env):
                client = TestClient(create_app())

                self.assertEqual(
                    client.get(
                        '/api/v1/universal/mobile-radar'
                    ).status_code,
                    401
                )

                login = client.post(
                    '/api/v1/auth/login',
                    json={
                        'username': 'testowner',
                        'password': 'safe-test-password-123'
                    }
                )

                self.assertEqual(
                    login.status_code,
                    200,
                    login.text
                )

                h = {
                    'Authorization': (
                        'Bearer '
                        + login.json()['access_token']
                    )
                }

                radar = client.get(
                    '/api/v1/universal/mobile-radar',
                    headers=h
                )

                self.assertEqual(
                    radar.status_code,
                    200,
                    radar.text
                )
                self.assertEqual(
                    radar.json()['items'],
                    []
                )

                self.assertEqual(
                    client.post(
                        '/api/v1/auth/logout',
                        headers=h
                    ).status_code,
                    200
                )

                self.assertEqual(
                    client.get(
                        '/api/v1/universal/mobile-radar',
                        headers=h
                    ).status_code,
                    401
                )
