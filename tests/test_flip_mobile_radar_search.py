import os
import sqlite3
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore


class RadarSearchHTTPTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        root = Path(self.tmp.name)
        auth_path = root / 'auth.db'

        auth = AuthStore(auth_path)
        auth.init_db()

        auth.create_owner(
            'owner-test',
            'valid-test-password-123',
        )

        with sqlite3.connect(
            root / 'offer_snapshots.db'
        ) as db:
            db.execute('''
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
            ''')

            data = (
                (1, 'OLX:1', 'PC RTX 3060'),
                (2, 'OLX:1', 'PC RTX 3060 nowszy'),
                (3, 'FB:2', 'PC RTX_4070'),
                (4, 'OLX:3', 'PC 50% rabatu'),
                (5, 'OLX:4', 'PC GTX 1660'),
            )

            for ident, key, title in data:
                db.execute(
                    '''
                    INSERT INTO snapshots
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ''',
                    (
                        ident,
                        key,
                        title,
                        'https://www.olx.pl/test',
                        900,
                        '{}',
                        '{}',
                        '{"action":"WATCH"}',
                        '2026-10-13',
                    ),
                )

        with patch.dict(os.environ, {
            'FLIP_API_AUTH_DB': str(auth_path),
            'FLIP_API_DATA_ROOT': str(root),
        }):
            from flip_core.mobile_api import create_app
            self.client = TestClient(create_app())

        response = self.client.post(
            '/api/v1/auth/login',
            json={
                'username': 'owner-test',
                'password': 'valid-test-password-123',
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        token = response.json()['access_token']

        self.headers = {
            'Authorization': 'Bearer ' + token,
        }

    def get(self, **params):
        return self.client.get(
            '/api/v1/radar',
            params=params,
            headers=self.headers,
        )

    def test_requires_login(self):
        response = self.client.get(
            '/api/v1/radar'
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_title_search_uses_latest_snapshot(self):
        response = self.get(q='RTX')

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        ids = [
            v['snapshot_id']
            for v in response.json()['items']
        ]

        self.assertEqual(ids, [3, 2])

    def test_literal_wildcards(self):
        percent = self.get(q='%').json()
        underscore = self.get(q='_').json()

        self.assertEqual(
            [
                v['snapshot_id']
                for v in percent['items']
            ],
            [4],
        )

        self.assertEqual(
            [
                v['snapshot_id']
                for v in underscore['items']
            ],
            [3],
        )

    def test_cursor_preserves_search(self):
        first = self.get(
            q='RTX',
            limit=1,
        ).json()

        second = self.get(
            q='RTX',
            limit=1,
            before_id=first['next_before_id'],
        ).json()

        self.assertEqual(
            [
                v['snapshot_id']
                for v in first['items']
            ],
            [3],
        )

        self.assertEqual(
            [
                v['snapshot_id']
                for v in second['items']
            ],
            [2],
        )

    def test_query_length_validation(self):
        response = self.get(q='x' * 121)

        self.assertEqual(
            response.status_code,
            422,
        )


if __name__ == '__main__':
    unittest.main()
