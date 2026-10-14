import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore
from flip_core.mobile_api import create_app


class HTTPRefreshReplayTest(unittest.TestCase):

    def test_revoked_family_and_independent_session(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / 'auth.sqlite'

            auth = AuthStore(db)
            auth.init_db()
            auth.create_owner(
                'owner',
                'test-password-12345'
            )

            env = {
                'FLIP_API_AUTH_DB': str(db),
                'FLIP_API_DATA_ROOT': td
            }

            with patch.dict(os.environ, env):
                api = TestClient(create_app())

                def login():
                    response = api.post(
                        '/api/v1/auth/login',
                        json={
                            'username': 'owner',
                            'password': 'test-password-12345'
                        }
                    )
                    self.assertEqual(
                        response.status_code,
                        200,
                        response.text
                    )
                    return response.json()

                a = login()
                b = login()

                def refresh(token):
                    return api.post(
                        '/api/v1/auth/refresh',
                        json={'refresh_token': token}
                    )

                r = refresh(a['refresh_token'])
                self.assertEqual(r.status_code, 200, r.text)
                a2 = r.json()

                r = refresh(a2['refresh_token'])
                self.assertEqual(r.status_code, 200, r.text)
                a3 = r.json()

                self.assertEqual(
                    refresh(a['refresh_token']).status_code,
                    401
                )

                def me(token):
                    return api.get(
                        '/api/v1/me',
                        headers={
                            'Authorization': 'Bearer ' + token
                        }
                    )

                self.assertEqual(
                    me(a3['access_token']).status_code,
                    401
                )

                self.assertEqual(
                    me(b['access_token']).status_code,
                    200
                )
