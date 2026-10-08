import sys
import unittest
from unittest.mock import patch


PROJECT_DIR = "/opt/olx-bot"

if PROJECT_DIR not in sys.path:
    sys.path.insert(
        0,
        PROJECT_DIR
    )


import price_resolver
import similarity_engine_v2
import valuation_v3
import watchdog


# ============================================================
# PRICE RESOLVER
# ============================================================

class TestPriceResolver(
    unittest.TestCase
):

    def test_normal_price(self):

        self.assertEqual(
            price_resolver.normalize_price(
                "2499 zł"
            ),
            2499
        )

    def test_price_with_spaces(self):

        self.assertEqual(
            price_resolver.normalize_price(
                "2 999 zł"
            ),
            2999
        )

    def test_price_with_decimal(self):

        self.assertEqual(
            price_resolver.normalize_price(
                "3 499,00 zł"
            ),
            3499
        )

    def test_integer_price(self):

        self.assertEqual(
            price_resolver.normalize_price(
                2200
            ),
            2200
        )

    def test_none_price(self):

        self.assertIsNone(
            price_resolver.normalize_price(
                None
            )
        )

    def test_invalid_price(self):

        self.assertIsNone(
            price_resolver.normalize_price(
                "Cena do negocjacji"
            )
        )

    def test_too_low_price(self):

        self.assertIsNone(
            price_resolver.normalize_price(
                50
            )
        )

    def test_json_ld_offer(self):

        data = {
            "@type": "Product",
            "name": "Komputer",
            "offers": {
                "@type": "Offer",
                "price": "2599"
            }
        }

        result = (
            price_resolver.find_price_in_json(
                data
            )
        )

        self.assertEqual(
            result,
            2599
        )

    def test_nested_json_ld(self):

        data = {
            "something": {
                "other": [
                    {
                        "@type": "Product",
                        "offers": {
                            "price": "3199"
                        }
                    }
                ]
            }
        }

        result = (
            price_resolver.find_price_in_json(
                data
            )
        )

        self.assertEqual(
            result,
            3199
        )


# ============================================================
# GPU SIMILARITY V2
# ============================================================

class TestGpuSimilarityV2(
    unittest.TestCase
):

    def test_exact_gpu(self):

        result = (
            similarity_engine_v2.gpu_similarity(
                "RTX 3060",
                "RTX 3060"
            )
        )

        self.assertEqual(
            result,
            1.0
        )

    def test_close_nvidia_gpu(self):

        result = (
            similarity_engine_v2.gpu_similarity(
                "RTX 3060",
                "RTX 3060 Ti"
            )
        )

        self.assertGreater(
            result,
            0.90
        )

        self.assertLess(
            result,
            1.0
        )

    def test_cross_brand_close_gpu(self):

        result = (
            similarity_engine_v2.gpu_similarity(
                "RTX 3060",
                "RX 6700 XT"
            )
        )

        self.assertGreater(
            result,
            0.85
        )

        self.assertLess(
            result,
            1.0
        )

    def test_far_gpu_rejected(self):

        result = (
            similarity_engine_v2.gpu_similarity(
                "RTX 3060",
                "RTX 4070"
            )
        )

        self.assertEqual(
            result,
            0.0
        )

    def test_price_normalization_gpu(self):

        result = (
            similarity_engine_v2
            .normalize_comparable_price(
                price=2700,

                target_cpu=
                    "Ryzen 5 5600",

                candidate_cpu=
                    "Ryzen 5 5600",

                target_gpu=
                    "RTX 3060",

                candidate_gpu=
                    "RTX 3060 Ti",

                target_ram=16,
                candidate_ram=16
            )
        )

        # RTX 3060 Ti ma wartość referencyjną
        # o 100 zł wyższą.
        #
        # 2700 - 100 = 2600.

        self.assertEqual(
            result,
            2600
        )


# ============================================================
# VALUATION V3 — WYBÓR ŹRÓDEŁ
# ============================================================

class TestValuationV3Selection(
    unittest.TestCase
):

    def empty_exact(self):

        return {
            "samples": 0,
            "quick_sale": None
        }

    def empty_same(self):

        return {
            "samples": 0,
            "quick_sale": None,
            "avg_similarity": None
        }

    def test_neighbor_cannot_dominate(self):

        static_quick = 1800

        exact = {
            "samples": 1,
            "quick_sale": 2100
        }

        same = {
            "samples": 5,
            "quick_sale": 2200,
            "avg_similarity": 94
        }

        neighbor = {
            "samples": 15,
            "quick_sale": 4000,
            "avg_similarity": 90
        }

        result = (
            valuation_v3.choose_value(
                static_quick,
                exact,
                same,
                neighbor
            )
        )

        self.assertTrue(
            result["ok"]
        )

        self.assertTrue(
            result[
                "neighbor_protected"
            ]
        )

        # 2200 * 1.20 = 2640.
        self.assertEqual(
            result[
                "neighbor_quick_protected"
            ],
            2640
        )

        # Neighbor nie może wyciągnąć
        # finalnej wyceny w okolice 4000.
        self.assertLess(
            result["quick_sale"],
            2200
        )

    def test_no_exact_neighbor_is_only_support(self):

        static_quick = 1800

        exact = {
            "samples": 0,
            "quick_sale": None
        }

        same = {
            "samples": 0,
            "quick_sale": None,
            "avg_similarity": None
        }

        neighbor = {
            "samples": 10,
            "quick_sale": 2400,
            "avg_similarity": 84
        }

        result = (
            valuation_v3.choose_value(
                static_quick,
                exact,
                same,
                neighbor
            )
        )

        self.assertTrue(
            result["ok"]
        )

        self.assertEqual(
            result[
                "valuation_source"
            ],
            "NEIGHBOR+STATIC"
        )

        # Neighbor 2400 zostanie ograniczony
        # do static * 1.20 = 2160.
        self.assertEqual(
            result[
                "neighbor_quick_protected"
            ],
            2160
        )

        # 75% static + 25% neighbor.
        self.assertEqual(
            result["quick_sale"],
            1890
        )

    def test_sanity_cap_v3(self):

        static_quick = 1800

        exact = {
            "samples": 1,
            "quick_sale": 3000
        }

        same = {
            "samples": 5,
            "quick_sale": 3000,
            "avg_similarity": 95
        }

        neighbor = {
            "samples": 10,
            "quick_sale": 3000,
            "avg_similarity": 92
        }

        result = (
            valuation_v3.choose_value(
                static_quick,
                exact,
                same,
                neighbor
            )
        )

        self.assertTrue(
            result[
                "sanity_cap_applied"
            ]
        )

        # 1 exact -> static * 1.20
        self.assertEqual(
            result[
                "sanity_cap"
            ],
            2160
        )

        self.assertEqual(
            result[
                "quick_sale"
            ],
            2160
        )


# ============================================================
# VALUATION V3 — PROFIT
# ============================================================

class TestValuationV3Profit(
    unittest.TestCase
):

    def setUp(self):

        self.patcher_static = patch(
            "valuation_v3.static_valuation"
        )

        self.patcher_exact = patch(
            "valuation_v3.get_cpu_gpu_stats"
        )

        self.patcher_same = patch(
            "valuation_v3.similar_market_stats"
        )

        self.patcher_neighbor = patch(
            "valuation_v3.similar_market_stats_v2"
        )

        self.mock_static = (
            self.patcher_static.start()
        )

        self.mock_exact = (
            self.patcher_exact.start()
        )

        self.mock_same = (
            self.patcher_same.start()
        )

        self.mock_neighbor = (
            self.patcher_neighbor.start()
        )

    def tearDown(self):

        patch.stopall()

    def prepare(
        self,
        quick_sale
    ):

        self.mock_static.return_value = {
            "ok": True,
            "quick_sale": quick_sale
        }

        self.mock_exact.return_value = {
            "samples": 10,
            "quick_sale": quick_sale,
            "min": quick_sale,
            "p25": quick_sale,
            "median": quick_sale,
            "p75": quick_sale
        }

        self.mock_same.return_value = {
            "samples": 10,
            "quick_sale": quick_sale,
            "avg_similarity": 100,
            "p25": quick_sale,
            "median": quick_sale
        }

        self.mock_neighbor.return_value = {
            "samples": 10,
            "exact_gpu_samples": 10,
            "neighbor_gpu_samples": 0,
            "quick_sale": quick_sale,
            "avg_similarity": 100,
            "p25": quick_sale,
            "median": quick_sale
        }

    def details(self):

        return {
            "price": 1400,
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": ["NVME 1 TB"]
        }

    def test_exact_400_profit(self):

        self.prepare(
            1950
        )

        result = (
            valuation_v3.estimate_flip_v3(
                self.details(),
                "POLSKA"
            )
        )

        # 1400 + 100 + 50 = 1550.
        # 1950 - 1550 = 400.

        self.assertEqual(
            result["profit"],
            400
        )

        self.assertTrue(
            result["profitable"]
        )

    def test_399_not_profitable(self):

        self.prepare(
            1949
        )

        result = (
            valuation_v3.estimate_flip_v3(
                self.details(),
                "POLSKA"
            )
        )

        self.assertEqual(
            result["profit"],
            399
        )

        self.assertFalse(
            result["profitable"]
        )

    def test_hot_700(self):

        self.prepare(
            2250
        )

        result = (
            valuation_v3.estimate_flip_v3(
                self.details(),
                "POLSKA"
            )
        )

        self.assertEqual(
            result["profit"],
            700
        )

        self.assertTrue(
            result["hot"]
        )


# ============================================================
# WATCHDOG
# ============================================================


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
