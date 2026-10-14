import unittest

from universal_v2.evidence import (
    SaleEvidence,
    permitted_comparables
)
from universal_v2.sources import Sources, SourceDenied


class Test23(unittest.TestCase):

    def policies(self):
        return Sources({
            'MANUAL': {
                'mode': 'IMPORT_ONLY',
                'operations': ['import', 'analyze']
            }
        })

    def test_no_sale_proof(self):
        with self.assertRaises(ValueError):
            SaleEvidence(
                'MANUAL', '1', 'GPU:x',
                10000, 'PLN', 'SALE_CONFIRMED'
            )

    def test_removed_is_not_sold(self):
        samples = [
            SaleEvidence(
                'MANUAL', '1', 'GPU:x',
                10000, 'PLN', 'REMOVED'
            )
        ]

        self.assertEqual(
            permitted_comparables(
                samples, self.policies()
            ),
            []
        )

    def test_blocked_platform(self):
        with self.assertRaises(SourceDenied):
            permitted_comparables(
                [
                    SaleEvidence(
                        'OLX', '1', 'GPU:x',
                        10000, 'PLN', 'ASKING'
                    )
                ],
                Sources()
            )

    def test_manual_verified(self):
        evidence = SaleEvidence(
            'MANUAL',
            'sale1',
            'GPU:x',
            10000,
            'PLN',
            'SALE_CONFIRMED',
            'invoice-001',
            True
        )

        result = permitted_comparables(
            [evidence], self.policies()
        )

        self.assertEqual(
            result[0].kind,
            'SOLD_VERIFIED'
        )
