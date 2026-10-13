import unittest

from universal_v2.manual_input import convert
from universal_v2.model import PriceKind


class Test13(unittest.TestCase):

    def test_manual(self):
        a = convert({
            'external_id': 'a',
            'title': 'RTX 3070',
            'price': '1200,50',
            'price_kind': 'FULL'
        })

        self.assertEqual(
            (
                a.source,
                a.price_minor,
                a.price_kind
            ),
            (
                'MANUAL',
                120050,
                PriceKind.FULL
            )
        )

    def test_no_spoof(self):
        with self.assertRaises(ValueError):
            convert({
                'external_id': 'a',
                'title': 'x',
                'source': 'OLX'
            })

    def test_no_price(self):
        self.assertIsNone(
            convert({
                'external_id': 'a',
                'title': 'x'
            }).price_minor
        )
