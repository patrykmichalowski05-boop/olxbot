import unittest

from universal_v2.comparables import (
    Comparable,
    estimate,
)


class Test08(unittest.TestCase):

    def setUp(self):
        self.c = [
            Comparable(
                'GPU:x',
                's1',
                100000,
                'SOLD_VERIFIED',
                'receipt',
            ),
            Comparable(
                'GPU:x',
                's2',
                110000,
                'SOLD_VERIFIED',
                'receipt',
            ),
            Comparable(
                'GPU:x',
                's3',
                120000,
                'SOLD_VERIFIED',
                'receipt',
            ),
        ]

    def test_median(self):
        self.assertEqual(
            estimate(
                self.c,
                'GPU:x',
            )['base_minor'],
            110000,
        )

    def test_different_variant(self):
        self.assertEqual(
            estimate(
                self.c,
                'GPU:y',
            )['status'],
            'NO_RELIABLE_VALUATION',
        )

    def test_exclude_self(self):
        self.assertEqual(
            estimate(
                self.c,
                'GPU:x',
                's1',
            )['status'],
            'NO_RELIABLE_VALUATION',
        )

    def test_asking_not_sale(self):
        rows = [
            Comparable(
                'GPU:x',
                str(i),
                100000,
                'ASKING',
            )
            for i in range(10)
        ]

        self.assertEqual(
            estimate(
                rows,
                'GPU:x',
            )['status'],
            'NO_RELIABLE_VALUATION',
        )
