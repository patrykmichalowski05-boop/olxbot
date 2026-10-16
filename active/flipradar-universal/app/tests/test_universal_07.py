import unittest

from universal_v2.model import Listing, PriceKind
from universal_v2.registry import identify


class Test07(unittest.TestCase):

    def item(
        self,
        size,
        auth='verified',
    ):
        return Listing(
            'MANUAL',
            '1',
            'Nike Dunk',
            25000,
            PriceKind.FULL,
            attributes={
                'brand': 'Nike',
                'model': 'Dunk',
                'size': size,
                'style_code': 'DD1391',
                'condition': 'GOOD',
                'authenticity': auth,
            },
        )

    def test_size(self):
        self.assertNotEqual(
            identify(
                'FASHION',
                self.item('42'),
            ).key,
            identify(
                'FASHION',
                self.item('43'),
            ).key,
        )

    def test_unknown_auth(self):
        self.assertIsNone(
            identify(
                'FASHION',
                self.item(
                    '42',
                    'unknown',
                ),
            ).key
        )

    def test_unknown_engine(self):
        with self.assertRaises(ValueError):
            identify(
                'TOYS',
                self.item('42'),
            )
