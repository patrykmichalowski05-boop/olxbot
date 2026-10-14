import tempfile
import unittest

from pathlib import Path
from universal_v2.watchlist_v2 import Watchlist


class Test26(unittest.TestCase):

    def test_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            watch = Watchlist(
                Path(d) / 'watch.db'
            )
            watch.init()

            watch.put(
                'user1', 'olx:12', 'RTX 3070'
            )

            watch.put(
                'user2', 'olx:12', 'inna oferta'
            )

            self.assertEqual(
                len(watch.get('user1')), 1
            )

            self.assertEqual(
                watch.get('user2')[0]['label'],
                'inna oferta'
            )

            self.assertTrue(
                watch.close('user1', 'olx:12')
            )

            self.assertFalse(
                watch.close('user1', 'olx:12')
            )

            self.assertEqual(
                watch.get('user1'), []
            )

            self.assertEqual(
                len(watch.get('user2')), 1
            )
