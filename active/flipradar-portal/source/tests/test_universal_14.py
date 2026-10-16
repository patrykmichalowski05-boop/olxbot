import unittest

from universal_v2.integration_status import (
    Integration,
    catalog,
)


class Test14(unittest.TestCase):

    def test_no_false_active(self):
        self.assertEqual(len(catalog()), 7)

        self.assertTrue(
            all(
                not x.auto_discovery_available
                for x in catalog()
            )
        )

    def test_invalid_active(self):
        with self.assertRaises(ValueError):
            Integration(
                'OTOMOTO',
                'ACTIVE'
            )
