import tempfile
import unittest
from pathlib import Path

from universal_v2.model import Listing, PriceKind
from universal_v2.guarded_pipeline import analyze_safe
from universal_v2.sources import Sources
from universal_v2.profiles import Profile
from universal_v2.store import Store
from universal_v2.outbox import Outbox


class Test22(unittest.TestCase):

    def setup_case(self, directory):
        store = Store(Path(directory) / 'db.sqlite')
        store.init()

        outbox = Outbox(Path(directory) / 'out.sqlite')
        outbox.init()

        policies = Sources({
            'MANUAL': {
                'mode': 'IMPORT_ONLY',
                'operations': [
                    'import', 'store', 'analyze', 'notify'
                ]
            }
        })

        return store, outbox, policies

    def test_installment_price(self):
        with tempfile.TemporaryDirectory() as d:
            store, outbox, sources = self.setup_case(d)

            row = Listing(
                'MANUAL',
                '1',
                'RTX 5060 Ti 16GB rata miesiecznie',
                100000,
                PriceKind.FULL
            )

            result = analyze_safe(
                row, 'ELECTRONICS',
                sources, Profile('u', 'PC'),
                store, outbox, [], {}
            )

            self.assertEqual(
                result['decision'],
                'NO_RELIABLE_VALUATION'
            )
            self.assertIn(
                'PAYMENT_TYPE_CONFLICT',
                result['reasons']
            )
            self.assertEqual(outbox.pending(), 0)

    def test_negative_cost(self):
        with tempfile.TemporaryDirectory() as d:
            store, outbox, sources = self.setup_case(d)

            with self.assertRaises(ValueError):
                analyze_safe(
                    Listing('MANUAL', '2', 'RTX', 1000),
                    'ELECTRONICS',
                    sources,
                    Profile('u', 'PC'),
                    store, outbox, [],
                    {'repair': -100}
                )
