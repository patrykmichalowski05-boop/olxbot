import unittest

from valuation_v3 import choose_value, sanity_cap


class ValuationGuardTests(unittest.TestCase):

    def test_one_sample_without_static(self):
        result = choose_value(
            None,
            {"samples": 1, "quick_sale": 5400},
            {"samples": 1, "quick_sale": 5400,
             "similarity": 100},
            {"samples": 1, "quick_sale": 5400,
             "similarity": 100},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["valuation_source"],
            "REJECT_NO_STATIC_LOW_SAMPLE"
        )

    def test_two_samples_without_static(self):
        result = choose_value(
            None,
            {"samples": 2, "quick_sale": 5400},
            {"samples": 2, "quick_sale": 5400},
            {"samples": 2, "quick_sale": 5400},
        )

        self.assertFalse(result["ok"])

    def test_static_sanity_cap(self):
        value, applied, cap = sanity_cap(
            5400, 1700, 1
        )

        self.assertEqual(value, 2040)
        self.assertTrue(applied)
        self.assertEqual(cap, 2040)


if __name__ == "__main__":
    unittest.main()
