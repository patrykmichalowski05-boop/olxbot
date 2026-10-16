import tempfile
import unittest

from pathlib import Path

from universal_v2.dev_radar import radar
from universal_v2.store import Store
from universal_v2.model import Listing


class Test20(unittest.TestCase):

    def test_filter_before_limit_and_owner(self):

        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'r.sqlite'

            s = Store(p)
            s.init()

            for n in range(5):

                title = (
                    'RTX ' + str(n)
                    if n == 0
                    else 'Phone ' + str(n)
                )

                obs, _ = s.observe(
                    Listing(
                        'MANUAL',
                        str(n),
                        title,
                        10000
                    )
                )

                s.valuation(
                    obs,
                    'v1',
                    'profile-u',
                    'market',
                    {'decision': 'REVIEW'}
                )

            self.assertEqual(
                len(
                    radar(
                        p,
                        'u',
                        q='RTX',
                        limit=1
                    )
                ),
                1
            )

            self.assertEqual(
                len(
                    radar(
                        p,
                        'intruder',
                        q='RTX'
                    )
                ),
                0
            )
