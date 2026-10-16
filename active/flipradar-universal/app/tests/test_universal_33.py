import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore
from universal_v2.mobile_bridge import create_app


class Test33(unittest.TestCase):

    def test_existing_mobile_login_and_new_radar(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            auth = AuthStore(root / 'auth.db')
            auth.init_db()

            auth.create_owner(
                'devowner',
                'test-password-strong-123'
            )

            environment = {
                'FLIP_API_AUTH_DB': str(
                    root / 'auth.db'
                ),
                'FLIP_API_DATA_ROOT': d,
                'FLIP_UNIVERSAL_DEV_DIR': d,
            }

            with patch.dict(os.environ, environment):
                client = TestClient(create_app())

                self.assertEqual(
                    client.get(
                        '/api/v1/universal/radar'
                    ).status_code,
                    401
                )

                login = client.post(
                    '/api/v1/auth/login',
                    json={
                        'username': 'devowner',
                        'password': 'test-password-strong-123'
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
                    client.get(
                        '/api/v1/me',
                        headers=headers
                    ).status_code,
                    200
                )

                response = client.get(
                    '/api/v1/universal/radar',
                    headers=headers
                )

                self.assertEqual(
                    response.status_code,
                    200,
                    response.text
                )

                self.assertEqual(
                    response.json()['items'],
                    []
                )

                self.assertEqual(
                    client.get(
                        '/api/v1/universal/status',
                        headers=headers
                    ).json()['automatic_sources'],
                    0
                )
