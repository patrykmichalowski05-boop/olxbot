import unittest
from backend.app.services.listing_history import history

class Test77(unittest.TestCase):
    def test_validation(self):
        for value in (0, 101, True):
            with self.assertRaises(ValueError):
                history(
                    None, 'workspace', 'listing',
                    limit=value
                )

        for value in (0, -1, True):
            with self.assertRaises(ValueError):
                history(
                    None, 'workspace', 'listing',
                    before_revision=value
                )
