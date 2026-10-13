import unittest
import tempfile

from pathlib import Path

from universal_v2.revision import save_revision
from universal_v2.store import Store
from universal_v2.model import Listing


class Test17(unittest.TestCase):

    def test_market_revision(self):
        with tempfile.TemporaryDirectory() as t:

            db = Store(
                Path(t) / 'revision.sqlite'
            )

            db.init()

            oid, _ = db.observe(
                Listing(
                    'MANUAL',
                    'a',
                    'GPU',
                    10000
                )
            )

            first = save_revision(
                db,
                oid,
                'engine-v1',
                'u',
                {'market': 1},
                {'value': 200}
            )

            again = save_revision(
                db,
                oid,
                'engine-v1',
                'u',
                {'market': 1},
                {'value': 200}
            )

            newer = save_revision(
                db,
                oid,
                'engine-v1',
                'u',
                {'market': 2},
                {'value': 220}
            )

            self.assertEqual(
                first[0],
                again[0]
            )

            self.assertNotEqual(
                first[0],
                newer[0]
            )

            with self.assertRaises(ValueError):
                save_revision(
                    db,
                    oid,
                    'engine-v1',
                    'u',
                    {'market': 1},
                    {'value': 999}
                )
