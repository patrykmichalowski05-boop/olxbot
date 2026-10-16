import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from flip_core.auth_store import AuthStore
from backend.app.api.security import WorkspaceSecurity


class Test53(unittest.TestCase):

    def test_bearer_auth(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "auth.db"
            store = AuthStore(path)

            store.init_db()
            uid = store.create_owner(
                "owner",
                "strong-password-123",
            )

            tokens = store.login(
                "owner",
                "strong-password-123",
            )

            security = WorkspaceSecurity(path)

            self.assertEqual(
                security.current_user(
                    "Bearer " + tokens["access_token"]
                ),
                uid,
            )

            with self.assertRaises(HTTPException):
                security.current_user("bad")

            with self.assertRaises(HTTPException):
                security.current_user(
                    "Bearer " + "x" * 44
                )

    def test_missing_db_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                WorkspaceSecurity(
                    Path(td) / "missing.db"
                )
