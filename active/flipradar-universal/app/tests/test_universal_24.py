import unittest

from universal_v2.market_audit import review_market
from universal_v2.evidence import SaleEvidence
from universal_v2.sources import Sources


class Test24(unittest.TestCase):

    def policies(self):
        return Sources({
            'MANUAL': {
                'mode': 'IMPORT_ONLY',
                'operations': ['import', 'analyze']
            }
        })

    def sales(self):
        return [
            SaleEvidence(
                'MANUAL',
                f's{i}',
                'GPU:a',
                10000 + i * 1000,
                'PLN',
                'SALE_CONFIRMED',
                f'proof{i}',
                True
            )
            for i in range(3)
        ]

    def test_market(self):
        result = review_market(
            self.sales(),
            self.policies(),
            'GPU:a'
        )

        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['verified_sales'], 3)

        different = review_market(
            self.sales(),
            self.policies(),
            'GPU:b'
        )

        self.assertEqual(
            different['status'],
            'NO_RELIABLE_VALUATION'
        )

        smaller = review_market(
            self.sales()[:2],
            self.policies(),
            'GPU:a'
        )

        self.assertNotEqual(
            result['market_id'],
            smaller['market_id']
        )

    def test_duplicate_sources(self):
        rows = [
            SaleEvidence(
                'MANUAL', 's1', 'GPU:a',
                11000, 'PLN', 'ASKING'
            )
            for _ in range(8)
        ]

        result = review_market(
            rows, self.policies(), 'GPU:a'
        )

        self.assertEqual(
            result['independent_observations'], 1
        )
