import tempfile
import unittest

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flip_core.auth_store import AuthStore
from flip_core.observations import ObservationStore


class Stage3Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_observation_versioning(self):
        store = ObservationStore(
            self.root / "observations.db"
        )
        store.init_db()

        first = store.observe(
            "OLX:1",
            {"price": 1000, "title": "PC"},
        )

        repeated = store.observe(
            "OLX:1",
            {"title": "PC", "price": 1000},
        )

        self.assertEqual(first, repeated)

        changed = store.observe(
            "OLX:1",
            {"price": 1000, "title": "PC updated"},
        )

        self.assertNotEqual(first, changed)

        old = store.value(
            first,
            "engine-1",
            "policy-1",
            "market-1",
            {"sale": 1800},
        )

        new = store.value(
            first,
            "engine-2",
            "policy-1",
            "market-1",
            {"sale": 1200},
        )

        self.assertNotEqual(old, new)

        with self.assertRaises(ValueError):
            store.value(
                first,
                "engine-1",
                "policy-1",
                "market-1",
                {"sale": 1200},
            )

        self.assertEqual(
            len(store.history("OLX:1")),
            3,
        )

    def test_observation_concurrency(self):
        store = ObservationStore(
            self.root / "observations.db"
        )
        store.init_db()

        def save(_):
            return store.observe(
                "FB:1",
                {"price": 900},
            )

        with ThreadPoolExecutor(
            max_workers=6
        ) as pool:
            results = list(
                pool.map(save, range(12))
            )

        self.assertEqual(
            len(set(results)),
            1,
        )

    def test_token_rotation_logout(self):
        auth = AuthStore(
            self.root / "auth.db"
        )
        auth.init_db()

        uid = auth.create_owner(
            "owner",
            "strong-test-password-123",
        )

        with self.assertRaises(ValueError):
            auth.login(
                "owner",
                "bad-password",
            )

        original = auth.login(
            "owner",
            "strong-test-password-123",
        )

        self.assertEqual(
            auth.verify_access(
                original["access_token"]
            ),
            uid,
        )

        fresh = auth.refresh(
            original["refresh_token"]
        )

        with self.assertRaises(ValueError):
            auth.verify_access(
                original["access_token"]
            )

        with self.assertRaises(ValueError):
            auth.refresh(
                original["refresh_token"]
            )

        self.assertEqual(
            auth.verify_access(
                fresh["access_token"]
            ),
            uid,
        )

        auth.logout(
            fresh["access_token"]
        )

        with self.assertRaises(ValueError):
            auth.verify_access(
                fresh["access_token"]
            )

    def test_pg_schema_and_mobile(self):
        root = Path(__file__).resolve().parents[1]

        sql = (
            root / "db/postgresql/001_initial.sql"
        ).read_text()

        for name in (
            "listings",
            "listing_observations",
            "valuation_runs",
            "deals",
            "deal_costs",
            "notification_outbox",
        ):
            self.assertIn(
                "CREATE TABLE IF NOT EXISTS " + name,
                sql,
            )

        mobile = (
            root / "mobile/src/api.ts"
        ).read_text()

        self.assertIn(
            "EXPO_PUBLIC_FLIP_API_URL",
            mobile,
        )


if __name__ == "__main__":
    unittest.main()
