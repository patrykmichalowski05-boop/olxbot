import unittest
import tempfile

from pathlib import Path

from universal_v2.profile_db import ProfileDB
from universal_v2.profiles import Profile


class Test18(unittest.TestCase):

    def test_user_separation(self):
        with tempfile.TemporaryDirectory() as t:

            db = ProfileDB(
                Path(t) / 'profiles.sqlite'
            )

            db.init()

            db.save(
                Profile(
                    'owner',
                    'pc',
                    min_profit_minor=40000
                )
            )

            self.assertEqual(
                db.get(
                    'owner',
                    'pc'
                ).min_profit_minor,
                40000
            )

            self.assertIsNone(
                db.get(
                    'other',
                    'pc'
                )
            )
