import unittest

from universal_v2.valuation import (
    calculate,
    decide,
)


class Test09(unittest.TestCase):

    def test_profit(self):
        result = calculate(
            100000,
            160000,
            {
                'repair': 10000,
                'fee': 5000,
            },
        )

        self.assertEqual(
            result['profit_minor'],
            45000,
        )

    def test_max_buy(self):
        result = calculate(
            100000,
            160000,
            {'repair': 10000},
            40000,
        )

        self.assertEqual(
            result['max_buy_minor'],
            110000,
        )

    def test_bad_cost(self):
        with self.assertRaises(ValueError):
            calculate(
                100000,
                160000,
                {'fee': -1},
            )

    def test_no_market(self):
        result = decide(
            {
                'status': 'NO_RELIABLE_VALUATION'
            },
            calculate(
                100000,
                160000,
                {},
            ),
            {
                'min_profit_minor': 10000,
                'min_roi_bps': 0,
            },
        )

        self.assertEqual(
            result,
            'NO_RELIABLE_VALUATION',
        )
