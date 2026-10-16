import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from flip_core.auth_store import AuthStore


class FlipMobilePreviewTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name)
        auth_path = root / 'auth.db'

        store = AuthStore(auth_path)
        store.init_db()

        store.create_owner(
            'testowner',
            'valid-test-password-123',
        )

        with patch.dict(os.environ, {
            'FLIP_API_AUTH_DB': str(auth_path),
            'FLIP_API_DATA_ROOT': str(root),
        }):
            from flip_core.mobile_api import create_app
            self.client = TestClient(create_app())

    def login_headers(self):
        response = self.client.post(
            '/api/v1/auth/login',
            json={
                'username': 'testowner',
                'password': 'valid-test-password-123',
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        token = response.json()['access_token']

        return {
            'Authorization': 'Bearer ' + token,
        }

    def test_requires_login(self):
        response = self.client.post(
            '/api/v1/valuations/preview',
            json={
                'purchase_minor': 150000,
                'sale_minor': 220000,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_correct_profit_and_roi(self):
        headers = self.login_headers()

        response = self.client.post(
            '/api/v1/valuations/preview',
            headers=headers,
            json={
                'purchase_minor': 150000,
                'sale_minor': 220000,
                'costs': {
                    'REPAIR': 10000,
                },
                'confidence': 'LOW',
                'condition': 'unknown',
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        data = response.json()

        self.assertEqual(
            data['operating_profit_minor'],
            60000,
        )

        self.assertEqual(
            data['total_investment_minor'],
            160000,
        )

        self.assertEqual(
            data['roi_bps'],
            3750,
        )

        self.assertEqual(
            data['decision'],
            'REVIEW',
        )

    def test_invalid_negative_purchase(self):
        headers = self.login_headers()

        response = self.client.post(
            '/api/v1/valuations/preview',
            headers=headers,
            json={
                'purchase_minor': -100,
                'sale_minor': 100000,
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
