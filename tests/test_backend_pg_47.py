import unittest

from pydantic import ValidationError
from backend.app.core.settings import Settings


class Test47(unittest.TestCase):

    def test_prod_requires_secret(self):
        with self.assertRaises(ValidationError):
            Settings(
                environment="production",
                database_url=(
                    "postgresql+psycopg://"
                    "test:pass@localhost/db"
                ),
                _env_file=None,
            )

    def test_rejects_non_postgres(self):
        with self.assertRaises(ValidationError):
            Settings(
                database_url="sqlite:///tmp/test.db",
                _env_file=None,
            )

    def test_development_config(self):
        cfg = Settings(
            database_url=(
                "postgresql+psycopg://"
                "test:pass@localhost/db"
            ),
            _env_file=None,
        )

        self.assertEqual(
            cfg.environment,
            "development",
        )
