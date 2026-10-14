import unittest

from universal_v2.readiness import report


class Test31(unittest.TestCase):

    def test_not_production_ready(self):
        result = report()

        self.assertEqual(
            result['offline_smoke'],
            'PASS'
        )

        self.assertFalse(
            result['production_ready']
        )

        self.assertEqual(
            result['platforms_automatic'],
            0
        )
