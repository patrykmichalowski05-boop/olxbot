import sqlite3
import tempfile
import unittest

from pathlib import Path
from flip_core.auth_store import AuthStore


PASSWORD = "correct-test-password-123"


class RefreshReplaySecurityTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.db = Path(self.tmp.name) / "auth.sqlite"
        self.auth = AuthStore(self.db)

        self.auth.init_db()
        self.auth.create_owner(
            "testowner",
            PASSWORD,
        )

    def test_replay_revokes_token_family(self):
        first = self.auth.login(
            "testowner", PASSWORD
        )

        other = self.auth.login(
            "testowner", PASSWORD
        )

        second = self.auth.refresh(
            first["refresh_token"]
        )

        third = self.auth.refresh(
            second["refresh_token"]
        )

        self.auth.verify_access(
            third["access_token"]
        )

        with self.assertRaises(ValueError):
            self.auth.refresh(
                first["refresh_token"]
            )

        with self.assertRaises(ValueError):
            self.auth.verify_access(
                third["access_token"]
            )

        # Oddzielne logowanie nadal dziala.
        self.auth.verify_access(
            other["access_token"]
        )

    def test_normal_refresh(self):
        first = self.auth.login(
            "testowner", PASSWORD
        )

        second = self.auth.refresh(
            first["refresh_token"]
        )

        self.auth.verify_access(
            second["access_token"]
        )

        with self.assertRaises(ValueError):
            self.auth.verify_access(
                first["access_token"]
            )

    def test_legacy_session(self):
        first = self.auth.login(
            "testowner", PASSWORD
        )

        with sqlite3.connect(self.db) as db:
            db.execute(
                "DELETE FROM session_lineage"
            )

        second = self.auth.refresh(
            first["refresh_token"]
        )

        self.auth.verify_access(
            second["access_token"]
        )

        with self.assertRaises(ValueError):
            self.auth.refresh(
                first["refresh_token"]
            )

        with self.assertRaises(ValueError):
            self.auth.verify_access(
                second["access_token"]
            )

    def test_unknown_token_is_safe(self):
        tokens = self.auth.login(
            "testowner", PASSWORD
        )

        with self.assertRaises(ValueError):
            self.auth.refresh("x" * 50)

        self.auth.verify_access(
            tokens["access_token"]
        )

    def test_schema_upgrade(self):
        with sqlite3.connect(self.db) as db:
            db.execute(
                "DROP TABLE session_lineage"
            )

        self.auth.init_db()

        first = self.auth.login(
            "testowner", PASSWORD
        )

        second = self.auth.refresh(
            first["refresh_token"]
        )

        self.auth.verify_access(
            second["access_token"]
        )


if __name__ == "__main__":
    unittest.main()
