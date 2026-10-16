import unittest

from universal_v2.model import Listing, PriceKind
from universal_v2.price_guard import check


class Test15(unittest.TestCase):

    def test_clean(self):
        row = Listing(
            'MANUAL',
            'a',
            'RTX 3070',
            10000,
            PriceKind.FULL
        )

        self.assertTrue(
            check(row)['ok']
        )

    def test_lease(self):
        row = Listing(
            'MANUAL',
            'a',
            'Tesla leasing rata',
            10000,
            PriceKind.FULL
        )

        self.assertFalse(
            check(row)['ok']
        )

    def test_bundle(self):
        row = Listing(
            'MANUAL',
            'a',
            'GPU',
            10000,
            PriceKind.FULL,
            quantity=2
        )

        self.assertFalse(
            check(row)['ok']
        )
