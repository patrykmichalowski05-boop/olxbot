import tempfile
import unittest

from pathlib import Path
from universal_v2.sandbox import database_file


class Test28(unittest.TestCase):

    def test_real_db_and_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            p = d / 'observations.sqlite'

            p.touch()

            self.assertEqual(
                database_file(d),
                p
            )

            p.unlink()
            p.symlink_to('/etc/passwd')

            with self.assertRaises(ValueError):
                database_file(d)

    def test_production_block(self):
        with self.assertRaises(ValueError):
            database_file('/opt/olx-bot')
