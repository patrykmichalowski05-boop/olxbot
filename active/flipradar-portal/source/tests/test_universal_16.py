import unittest

from universal_v2.market_guard import review
from universal_v2.comparables import Comparable


class Test16(unittest.TestCase):

    def test_askings_are_not_sales(self):
        rows = [
            Comparable(
                'x',
                str(i),
                10000,
                'ASKING'
            )
            for i in range(4)
        ]

        result = review(rows, 'x')

        self.assertEqual(
            result['confirmed_sales'],
            0
        )

        self.assertNotEqual(
            result['status'],
            'OK'
        )

    def test_proof_required(self):
        with self.assertRaises(ValueError):
            Comparable(
                'x',
                'a',
                1000,
                'SOLD_VERIFIED'
            )
