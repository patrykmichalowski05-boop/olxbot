import unittest

from universal_v2.model import (
    Listing,
    PriceKind,
)

from universal_v2.electronics import (
    classify_electronics as identify,
)


class Test05(unittest.TestCase):

    def item(self, title):
        return Listing(
            'MANUAL',
            'id',
            title,
            100000,
            PriceKind.FULL,
        )

    def test_vram(self):
        self.assertNotEqual(
            identify(
                self.item('RTX 5060 Ti 8GB')
            ).key,
            identify(
                self.item('RTX 5060 Ti 16GB')
            ).key,
        )

    def test_phone(self):
        self.assertNotEqual(
            identify(
                self.item(
                    'iPhone 15 Pro 128GB'
                )
            ).key,
            identify(
                self.item(
                    'iPhone 15 Pro 256GB'
                )
            ).key,
        )

    def test_box(self):
        self.assertIsNone(
            identify(
                self.item(
                    'iPhone 15 Pro 256GB samo pudełko'
                )
            ).key
        )

    def test_missing(self):
        self.assertIsNone(
            identify(
                self.item('RTX 3070')
            ).key
        )
