import os
import sys
import tempfile
import unittest


# ============================================================
# IMPORT PROJEKTU
# ============================================================

PROJECT_DIR = "/opt/olx-bot"

if PROJECT_DIR not in sys.path:
    sys.path.insert(
        0,
        PROJECT_DIR
    )


import database
import decision_log
import valuation_v2

from filters import hardware_ok

from ai_analyzer import (
    apply_ai_adjustment
)

from spec_recovery import (
    evidence_exists,
    missing_specs
)

from scanner import (
    get_offer_id,
    parse_card_price
)


# ============================================================
# HARDWARE FILTER
# ============================================================

class TestHardwareFilter(
    unittest.TestCase
):

    def test_i5_8400_rejected(self):

        details = {
            "cpu": "i5-8400",
            "gpu": "GTX 1660",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertFalse(
            ok
        )

    def test_i5_9400_accepted(self):

        details = {
            "cpu": "i5-9400",
            "gpu": "GTX 1660",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertTrue(
            ok,
            msg=str(reasons)
        )

    def test_i5_10400f_accepted(self):

        details = {
            "cpu": "i5-10400F",
            "gpu": "RTX 3060",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertTrue(
            ok,
            msg=str(reasons)
        )

    def test_ryzen_2600_rejected(self):

        details = {
            "cpu": "Ryzen 5 2600",
            "gpu": "GTX 1660",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertFalse(
            ok
        )

    def test_ryzen_3600_accepted(self):

        details = {
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertTrue(
            ok,
            msg=str(reasons)
        )

    def test_8gb_rejected(self):

        details = {
            "cpu": "Ryzen 5 5600",
            "gpu": "RTX 3060",
            "ram": 8
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertFalse(
            ok
        )

    def test_16gb_accepted(self):

        details = {
            "cpu": "Ryzen 5 5600",
            "gpu": "RTX 3060",
            "ram": 16
        }

        ok, reasons = hardware_ok(
            details
        )

        self.assertTrue(
            ok,
            msg=str(reasons)
        )


# ============================================================
# OLX ID
# ============================================================

class TestOfferId(
    unittest.TestCase
):

    def test_real_olx_id_not_cid99(self):

        url = (
            "https://www.olx.pl/d/oferta/"
            "komputer-gamingowy-"
            "CID99-ID1cy7iC.html"
        )

        result = get_offer_id(
            url
        )

        self.assertEqual(
            result,
            "ID1cy7iC"
        )

    def test_second_real_id(self):

        url = (
            "https://www.olx.pl/d/oferta/"
            "pc-rtx-3060-"
            "CID99-ID17NYIm.html"
        )

        result = get_offer_id(
            url
        )

        self.assertEqual(
            result,
            "ID17NYIm"
        )

    def test_never_returns_id99(self):

        url = (
            "https://www.olx.pl/d/oferta/"
            "pc-CID99-ID1abcXYZ.html"
        )

        result = get_offer_id(
            url
        )

        self.assertNotEqual(
            result,
            "ID99"
        )


# ============================================================
# CENA Z KARTY OLX
# ============================================================

class TestCardPrice(
    unittest.TestCase
):

    def test_price_1400(self):

        text = """
        Komputer gamingowy
        1 400 zł
        Używane
        """

        self.assertEqual(
            parse_card_price(text),
            1400
        )

    def test_price_2999(self):

        text = """
        Ryzen RTX
        2 999 zł
        """

        self.assertEqual(
            parse_card_price(text),
            2999
        )

    def test_no_price(self):

        text = (
            "Komputer bez ceny"
        )

        self.assertIsNone(
            parse_card_price(text)
        )


# ============================================================
# SPEC RECOVERY — BEZ API
# ============================================================

class TestSpecRecovery(
    unittest.TestCase
):

    def test_missing_specs(self):

        details = {
            "cpu": None,
            "gpu": "RTX 3060",
            "ram": None
        }

        result = missing_specs(
            details
        )

        self.assertIn(
            "cpu",
            result
        )

        self.assertIn(
            "ram",
            result
        )

        self.assertNotIn(
            "gpu",
            result
        )

    def test_evidence_exists(self):

        source = (
            "Procesor Ryzen 5 5600. "
            "Karta RTX 3060 Ti 8GB."
        )

        self.assertTrue(
            evidence_exists(
                source,
                "Ryzen 5 5600"
            )
        )

    def test_fake_evidence_rejected(self):

        source = (
            "Komputer bardzo wydajny."
        )

        self.assertFalse(
            evidence_exists(
                source,
                "RTX 4070"
            )
        )


# ============================================================
# AI KOREKTA CENY — BEZ WYWOŁANIA API
# ============================================================

class TestAIAdjustment(
    unittest.TestCase
):

    def test_zero_adjustment(self):

        valuation = {
            "quick_sale": 2000,
            "total_cost": 1500,
            "profit": 500,
            "profitable": True,
            "hot": False
        }

        ai = {
            "ok": True,
            "adjustment_percent": 0,
            "condition": "normal",
            "confidence": 0.9,
            "issues": [],
            "missing_info": [],
            "summary": "OK"
        }

        result = (
            apply_ai_adjustment(
                valuation,
                ai
            )
        )

        self.assertEqual(
            result["quick_sale"],
            2000
        )

        self.assertEqual(
            result["profit"],
            500
        )

    def test_minus_12_percent(self):

        valuation = {
            "quick_sale": 2000,
            "total_cost": 1500,
            "profit": 500,
            "profitable": True,
            "hot": False
        }

        ai = {
            "ok": True,
            "adjustment_percent": -12,
            "condition": "risk",
            "confidence": 0.9,
            "issues": [
                "GPU po kopaniu"
            ],
            "missing_info": [],
            "summary": "Ryzyko"
        }

        result = (
            apply_ai_adjustment(
                valuation,
                ai
            )
        )

        self.assertEqual(
            result["quick_sale"],
            1760
        )

        self.assertEqual(
            result["profit"],
            260
        )

        self.assertFalse(
            result["profitable"]
        )

    def test_ai_can_drop_below_threshold(self):

        valuation = {
            "quick_sale": 2050,
            "total_cost": 1550,
            "profit": 500,
            "profitable": True,
            "hot": False
        }

        ai = {
            "ok": True,
            "adjustment_percent": -10,
            "condition": "risk",
            "confidence": 0.95,
            "issues": [],
            "missing_info": [],
            "summary": ""
        }

        result = (
            apply_ai_adjustment(
                valuation,
                ai
            )
        )

        self.assertLess(
            result["profit"],
            400
        )

        self.assertFalse(
            result["profitable"]
        )


# ============================================================
# DATABASE — PRICE DROP
# ============================================================

class TestPriceDropDatabase(
    unittest.TestCase
):

    def setUp(self):

        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )

        self.old_db_file = (
            database.DB_FILE
        )

        database.DB_FILE = os.path.join(
            self.temp_dir.name,
            "test_olx.db"
        )

        database.init_db()

    def tearDown(self):

        database.DB_FILE = (
            self.old_db_file
        )

        self.temp_dir.cleanup()

    def test_new_offer_requires_analysis(self):

        result = database.observe_offer(
            "IDTEST1",
            "Test PC",
            2000,
            "https://example.com"
        )

        self.assertTrue(
            result["is_new"]
        )

        self.assertTrue(
            result["should_analyze"]
        )

        self.assertEqual(
            result["reason"],
            "NEW"
        )

    def test_unchanged_price_skipped_after_analysis(self):

        database.observe_offer(
            "IDTEST2",
            "Test PC",
            2000,
            "https://example.com"
        )

        database.mark_analyzed(
            "IDTEST2",
            2000
        )

        result = database.observe_offer(
            "IDTEST2",
            "Test PC",
            2000,
            "https://example.com"
        )

        self.assertFalse(
            result["should_analyze"]
        )

        self.assertEqual(
            result["reason"],
            "UNCHANGED"
        )

    def test_price_drop_reanalyzed(self):

        database.observe_offer(
            "IDTEST3",
            "Test PC",
            2200,
            "https://example.com"
        )

        database.mark_analyzed(
            "IDTEST3",
            2200
        )

        result = database.observe_offer(
            "IDTEST3",
            "Test PC",
            1700,
            "https://example.com"
        )

        self.assertTrue(
            result["price_drop"]
        )

        self.assertTrue(
            result["should_analyze"]
        )

        self.assertEqual(
            result["reason"],
            "PRICE_DROP"
        )

        self.assertEqual(
            result["previous_price"],
            2200
        )

        self.assertEqual(
            result["current_price"],
            1700
        )

    def test_price_increase_not_reanalyzed(self):

        database.observe_offer(
            "IDTEST4",
            "Test PC",
            1800,
            "https://example.com"
        )

        database.mark_analyzed(
            "IDTEST4",
            1800
        )

        result = database.observe_offer(
            "IDTEST4",
            "Test PC",
            2000,
            "https://example.com"
        )

        self.assertFalse(
            result["should_analyze"]
        )


# ============================================================
# VALUATION V2 — MOCKOWANE DANE RYNKOWE
# ============================================================

class TestValuationV2(
    unittest.TestCase
):

    def setUp(self):

        self.old_static = (
            valuation_v2.static_valuation
        )

        self.old_exact = (
            valuation_v2.get_cpu_gpu_stats
        )

        self.old_similar = (
            valuation_v2.similar_market_stats
        )

    def tearDown(self):

        valuation_v2.static_valuation = (
            self.old_static
        )

        valuation_v2.get_cpu_gpu_stats = (
            self.old_exact
        )

        valuation_v2.similar_market_stats = (
            self.old_similar
        )

    def mock_market(
        self,
        quick_sale
    ):

        return {
            "samples": 5,
            "quick_sale": quick_sale,
            "min": 2000,
            "p25": 2100,
            "median": 2200,
            "p75": 2300
        }

    def mock_similar(
        self,
        quick_sale
    ):

        return {
            "samples": 8,
            "quick_sale": quick_sale,
            "avg_similarity": 95,
            "median": 2200,
            "p25": 2100
        }

    def test_400_profit_is_profitable(self):

        valuation_v2.static_valuation = (
            lambda details: {
                "ok": True,
                "quick_sale": 1950
            }
        )

        valuation_v2.get_cpu_gpu_stats = (
            lambda *args, **kwargs:
                self.mock_market(
                    1950
                )
        )

        valuation_v2.similar_market_stats = (
            lambda *args, **kwargs:
                self.mock_similar(
                    1950
                )
        )

        details = {
            "price": 1400,
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": []
        }

        result = (
            valuation_v2.estimate_flip_v2(
                details,
                "POLSKA"
            )
        )

        # 1400 + 100 reserve + 50 shipping
        # = 1550
        #
        # 1950 - 1550 = 400

        self.assertEqual(
            result["profit"],
            400
        )

        self.assertTrue(
            result["profitable"]
        )

    def test_399_profit_not_profitable(self):

        valuation_v2.static_valuation = (
            lambda details: {
                "ok": True,
                "quick_sale": 1949
            }
        )

        valuation_v2.get_cpu_gpu_stats = (
            lambda *args, **kwargs:
                self.mock_market(
                    1949
                )
        )

        valuation_v2.similar_market_stats = (
            lambda *args, **kwargs:
                self.mock_similar(
                    1949
                )
        )

        details = {
            "price": 1400,
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": []
        }

        result = (
            valuation_v2.estimate_flip_v2(
                details,
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

    def test_hot_from_700(self):

        valuation_v2.static_valuation = (
            lambda details: {
                "ok": True,
                "quick_sale": 2250
            }
        )

        valuation_v2.get_cpu_gpu_stats = (
            lambda *args, **kwargs:
                self.mock_market(
                    2250
                )
        )

        valuation_v2.similar_market_stats = (
            lambda *args, **kwargs:
                self.mock_similar(
                    2250
                )
        )

        details = {
            "price": 1400,
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": []
        }

        result = (
            valuation_v2.estimate_flip_v2(
                details,
                "POLSKA"
            )
        )

        # 2250 - 1550 = 700

        self.assertEqual(
            result["profit"],
            700
        )

        self.assertTrue(
            result["hot"]
        )

    def test_sanity_cap_protects_bad_market(self):

        valuation_v2.static_valuation = (
            lambda details: {
                "ok": True,
                "quick_sale": 1800
            }
        )

        valuation_v2.get_cpu_gpu_stats = (
            lambda *args, **kwargs: {
                "samples": 0,
                "quick_sale": None,
                "min": None,
                "p25": None,
                "median": None,
                "p75": None
            }
        )

        valuation_v2.similar_market_stats = (
            lambda *args, **kwargs: {
                "samples": 10,
                "quick_sale": 3500,
                "avg_similarity": 95,
                "median": 3600,
                "p25": 3400
            }
        )

        details = {
            "price": 1500,
            "cpu": "i5-12400F",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": []
        }

        result = (
            valuation_v2.estimate_flip_v2(
                details,
                "POLSKA"
            )
        )

        # Brak exact -> max 115% static
        # 1800 * 1.15 = 2070

        self.assertTrue(
            result[
                "sanity_cap_applied"
            ]
        )

        self.assertLessEqual(
            result["quick_sale"],
            2070
        )


# ============================================================
# DECISION LOG — TEMP DB
# ============================================================

class TestDecisionLog(
    unittest.TestCase
):

    def setUp(self):

        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )

        self.old_db_file = (
            decision_log.DB_FILE
        )

        decision_log.DB_FILE = (
            os.path.join(
                self.temp_dir.name,
                "decisions.db"
            )
        )

        decision_log.init_decision_db()

    def tearDown(self):

        decision_log.DB_FILE = (
            self.old_db_file
        )

        self.temp_dir.cleanup()

    def test_decision_saved(self):

        details = {
            "title": "Test",
            "price": 1400,
            "cpu": "Ryzen 5 3600",
            "gpu": "RTX 3060",
            "ram": 16,
            "disks": []
        }

        valuation = {
            "quick_sale": 2000,
            "total_cost": 1550,
            "profit": 450,
            "valuation_source":
                "TEST",
            "confidence":
                "TEST"
        }

        decision_log.log_decision(
            offer_id="IDLOG1",
            details=details,
            valuation=valuation,
            mode="POLSKA",
            offer_url=
                "https://example.com",
            decision="ACCEPT",
            reason="TEST",
            stage="FINAL"
        )

        result = (
            decision_log.stats()
        )

        self.assertEqual(
            result["total"],
            1
        )

        self.assertEqual(
            result["accepted"],
            1
        )

        self.assertEqual(
            result["rejected"],
            0
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
