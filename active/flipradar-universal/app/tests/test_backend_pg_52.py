import unittest

from backend.app.db.session import make_session_factory


class Test52(unittest.TestCase):

    def test_rejects_sqlite(self):
        with self.assertRaises(ValueError):
            make_session_factory("sqlite:///test.db")

    def test_lazy_postgres_engine(self):
        engine, factory = make_session_factory(
            "postgresql+psycopg://"
            "test:pass@127.0.0.1/test"
        )

        try:
            self.assertEqual(
                engine.dialect.name,
                "postgresql",
            )

            self.assertFalse(
                factory.kw["autoflush"]
            )

        finally:
            engine.dispose()
