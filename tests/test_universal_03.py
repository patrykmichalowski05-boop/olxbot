import unittest

from universal_v2.sources import (
    Sources,
    SourceDenied,
)

from universal_v2.model import Listing


class Test03(unittest.TestCase):

    def setUp(self):
        self.offer = Listing(
            'OLX',
            '1',
            'RTX',
            10000,
        )

    def test_blocked(self):
        with self.assertRaises(SourceDenied):
            Sources().check(
                self.offer,
                'fetch',
            )

    def test_import(self):
        cfg = {
            'OLX': {
                'mode': 'IMPORT_ONLY',
                'operations': [
                    'import',
                    'analyze',
                    'store',
                ],
            }
        }

        Sources(cfg).check(
            self.offer,
            'import',
        )

    def test_scraping_denied(self):
        cfg = {
            'OLX': {
                'mode': 'IMPORT_ONLY',
                'operations': ['fetch'],
            }
        }

        with self.assertRaises(SourceDenied):
            Sources(cfg).check(
                self.offer,
                'fetch',
            )

    def test_unverified_denied(self):
        cfg = {
            'OLX': {
                'mode': 'AUTHORIZED',
                'operations': ['fetch'],
            }
        }

        with self.assertRaises(SourceDenied):
            Sources(cfg).check(
                self.offer,
                'fetch',
            )
