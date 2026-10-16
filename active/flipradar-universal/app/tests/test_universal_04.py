import unittest
import tempfile

from pathlib import Path

from universal_v2.store import Store
from universal_v2.model import Listing


class Test04(unittest.TestCase):

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)

        self.db = Store(
            Path(t.name) / 'test.db'
        )

        self.db.init()

    def test_repeat(self):
        a = Listing(
            'MANUAL',
            'a',
            'Telefon',
            10000,
        )

        self.assertTrue(
            self.db.observe(a)[1]
        )

        self.assertFalse(
            self.db.observe(a)[1]
        )

    def test_description_change(self):
        a = Listing(
            'MANUAL',
            'a',
            'Telefon',
            10000,
            description='A',
        )

        b = Listing(
            'MANUAL',
            'a',
            'Telefon',
            10000,
            description='B',
        )

        self.assertNotEqual(
            self.db.observe(a)[0],
            self.db.observe(b)[0],
        )

    def test_valuation_repeat(self):
        x = self.db.observe(
            Listing(
                'MANUAL',
                'a',
                'GPU',
                20000,
            )
        )[0]

        self.assertTrue(
            self.db.valuation(
                x,
                'v1',
                'p1',
                'm1',
                {'profit': 1},
            )[1]
        )

        self.assertFalse(
            self.db.valuation(
                x,
                'v1',
                'p1',
                'm1',
                {'profit': 1},
            )[1]
        )

    def test_valuation_collision(self):
        x = self.db.observe(
            Listing(
                'MANUAL',
                'a',
                'GPU',
                20000,
            )
        )[0]

        self.db.valuation(
            x,
            'v1',
            'p1',
            'm1',
            {'profit': 1},
        )

        with self.assertRaises(ValueError):
            self.db.valuation(
                x,
                'v1',
                'p1',
                'm1',
                {'profit': 2},
            )
