import unittest

from bundle_valuation import (
    apply_bundle_valuation
)


class TestBundleValuation(
    unittest.TestCase
):

    def base(self):

        return {
            "ok": True,

            "quick_sale":
                5000,

            "total_cost":
                4150,

            "profit":
                850,

            "profitable":
                True,

            "hot":
                True,
        }

    def test_normal_pc_unchanged(self):

        result = (
            apply_bundle_valuation(
                self.base(),
                {
                    "is_bundle": False
                }
            )
        )

        self.assertEqual(
            result["quick_sale"],
            5000
        )

        self.assertEqual(
            result["profit"],
            850
        )

    def test_high_bundle_full_bonus(self):

        result = (
            apply_bundle_valuation(
                self.base(),
                {
                    "is_bundle": True,
                    "strong_bundle": True,
                    "confidence": "HIGH",
                    "score": 8,

                    "accessory_quick_value":
                        1500,

                    "items": [],
                }
            )
        )

        self.assertEqual(
            result[
                "bundle_accessory_value"
            ],
            1500
        )

        self.assertEqual(
            result["quick_sale"],
            6500
        )

        self.assertEqual(
            result["profit"],
            2350
        )

    def test_medium_bundle_discount(self):

        result = (
            apply_bundle_valuation(
                self.base(),
                {
                    "is_bundle": True,
                    "strong_bundle": False,
                    "confidence": "MEDIUM",
                    "score": 4,

                    "accessory_quick_value":
                        1000,

                    "items": [],
                }
            )
        )

        self.assertEqual(
            result[
                "bundle_accessory_value"
            ],
            700
        )

        self.assertEqual(
            result["quick_sale"],
            5700
        )

    def test_low_bundle_no_auto_bonus(self):

        result = (
            apply_bundle_valuation(
                self.base(),
                {
                    "is_bundle": True,
                    "strong_bundle": False,
                    "confidence": "LOW",
                    "score": 2,

                    "accessory_quick_value":
                        1000,

                    "items": [],
                }
            )
        )

        self.assertEqual(
            result[
                "bundle_accessory_value"
            ],
            0
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
