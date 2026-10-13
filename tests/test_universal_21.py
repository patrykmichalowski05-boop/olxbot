import unittest

from universal_v2.smoke import run


class Test21(unittest.TestCase):

    def test_offline_end_to_end(self):
        result = run()

        self.assertEqual(
            result['status'],
            'PASS'
        )

        self.assertEqual(
            result['notifications'],
            0
        )
