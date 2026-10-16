import unittest

from universal_v2.model import (
    minor,
    Listing,
    PriceKind,
)


class Test02(unittest.TestCase):

    def test_money(self):
        self.assertEqual(
            minor('1250,50'),
            125050,
        )

    def test_reject_float(self):
        with self.assertRaises(ValueError):
            minor(2.3)

    def test_reject_subcent(self):
        with self.assertRaises(ValueError):
            minor('2.001')

    def test_listing(self):
        listing = Listing(
            'MANUAL',
            '1',
            'RTX',
            10000,
            PriceKind.FULL,
        )

        self.assertEqual(
            listing.currency,
            'PLN',
        )
