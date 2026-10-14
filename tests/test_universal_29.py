import tempfile
import unittest

from pathlib import Path

from universal_v2.store import Store
from universal_v2.model import Listing
from universal_v2.radar_service import RadarService


class Test29(unittest.TestCase):

    def test_user_scope(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / 'observations.sqlite'

            store = Store(db)
            store.init()

            oid, _ = store.observe(
                Listing(
                    'MANUAL',
                    'x',
                    'RTX 3070',
                    10000
                )
            )

            store.valuation(
                oid,
                'v1',
                'profile-u',
                'm1',
                {'decision': 'WATCH'}
            )

            self.assertEqual(
                len(
                    RadarService(db).page(
                        'u'
                    )['items']
                ),
                1
            )

            self.assertEqual(
                RadarService(db).page(
                    'other'
                )['items'],
                []
            )
