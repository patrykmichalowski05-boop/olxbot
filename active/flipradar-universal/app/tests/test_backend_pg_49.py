import os
import subprocess
import sys
import unittest


class Test49(unittest.TestCase):

    def test_offline_postgres_migration(self):
        env = os.environ.copy()

        env["FLIP_BACKEND_DATABASE_URL"] = (
            "postgresql+psycopg://"
            "test:pass@localhost/testdb"
        )

        done = subprocess.run(
            [
                sys.executable,
                "-m", "alembic",
                "-c", "backend/alembic.ini",
                "upgrade", "head", "--sql",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn(
            "CREATE TABLE users",
            done.stdout,
        )

        self.assertIn(
            "CREATE TABLE outbox_events",
            done.stdout,
        )
