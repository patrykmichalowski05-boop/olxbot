import tempfile
import unittest

from pathlib import Path
from universal_v2.ledger_v2 import Ledger


class Test25(unittest.TestCase):

    def test_costs_and_profit(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Ledger(Path(d) / 'ledger.db')
            ledger.init()

            first = ledger.record(
                'u', 'pc1', 'buy1',
                'PURCHASE', 100000
            )

            repeated = ledger.record(
                'u', 'pc1', 'buy1',
                'PURCHASE', 100000
            )

            self.assertEqual(
                repeated, (first[0], False)
            )

            ledger.record(
                'u', 'pc1', 'cost1',
                'COST', 12000
            )

            ledger.record(
                'u', 'pc1', 'cost2',
                'COST', 3000
            )

            ledger.record(
                'u', 'pc1', 'sell1',
                'SALE', 170000
            )

            self.assertEqual(
                ledger.totals(
                    'u', 'pc1'
                )['realized_profit_minor'],
                55000
            )

            self.assertIsNone(
                ledger.totals('other', 'pc1')
            )

            with self.assertRaises(ValueError):
                ledger.record(
                    'u', 'pc1', 'sell2',
                    'SALE', 170000
                )

    def test_request_key_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Ledger(Path(d) / 'ledger.db')
            ledger.init()

            ledger.record(
                'u', 'a', 'key',
                'PURCHASE', 1000
            )

            with self.assertRaises(ValueError):
                ledger.record(
                    'u', 'b', 'key',
                    'PURCHASE', 2000
                )

    def test_cost_requires_purchase(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Ledger(Path(d) / 'ledger.db')
            ledger.init()

            with self.assertRaises(ValueError):
                ledger.record(
                    'u', 'pc', 'cost1',
                    'COST', 1000
                )
