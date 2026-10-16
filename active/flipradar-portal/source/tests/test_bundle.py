import unittest

from bundle_detector import (
    analyze_bundle
)


class TestBundleDetector(
    unittest.TestCase
):

    def test_normal_pc_not_bundle(self):

        result = analyze_bundle({
            "title":
                "Ryzen 5 5600 RTX 3060 16GB",
            "description":
                "Komputer gamingowy"
        })

        self.assertFalse(
            result["is_bundle"]
        )

    def test_pc_monitor_bundle(self):

        result = analyze_bundle({
            "title":
                "Komputer gamingowy + monitor 27",
            "description":
                ""
        })

        self.assertTrue(
            result["is_bundle"]
        )

    def test_mega_setup(self):

        result = analyze_bundle({
            "title":
                (
                    "Kompletny Mega Setup 4K VR "
                    "RTX 4070 Ti i5-13600K "
                    "Monitor LG 32 NanoIPS "
                    "T300RS GT TH8A HOTAS"
                ),

            "description":
                ""
        })

        self.assertTrue(
            result["strong_bundle"]
        )

        self.assertGreaterEqual(
            result["accessory_quick_value"],
            1500
        )

    def test_t300_detected(self):

        result = analyze_bundle({
            "title":
                "PC + T300RS GT",
            "description":
                "kierownica Thrustmaster"
        })

        types = [
            item["type"]
            for item
            in result["items"]
        ]

        self.assertIn(
            "wheel",
            types
        )

    def test_th8a_detected(self):

        result = analyze_bundle({
            "title":
                "Setup gamingowy",
            "description":
                "Thrustmaster TH8A"
        })

        types = [
            item["type"]
            for item
            in result["items"]
        ]

        self.assertIn(
            "shifter",
            types
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
