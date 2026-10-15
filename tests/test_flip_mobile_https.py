import runpy
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODULE = runpy.run_path(
    str(
        ROOT
        / "mobile/scripts/check_https_api.py"
    ),
    run_name="flip_https_tests",
)

validate_url = MODULE["validate_url"]


class MobileHTTPSTests(unittest.TestCase):

    def test_valid_https(self):
        self.assertEqual(
            validate_url(
                "https://api.example.com/"
            ),
            "https://api.example.com",
        )

    def test_reject_http(self):
        with self.assertRaises(ValueError):
            validate_url(
                "http://api.example.com"
            )

    def test_reject_credentials(self):
        with self.assertRaises(ValueError):
            validate_url(
                "https://user:pass@api.example.com"
            )

    def test_reject_path(self):
        with self.assertRaises(ValueError):
            validate_url(
                "https://api.example.com/api/v1"
            )

    def test_reject_placeholder(self):
        with self.assertRaises(ValueError):
            validate_url(
                "https://api.example.invalid"
            )

    def test_mobile_diagnostics_present(self):
        api = (
            ROOT / "mobile/src/api/client.ts"
        ).read_text(encoding="utf-8")

        app = (
            ROOT / "mobile/src/app/(auth)/login.tsx"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "checkApiReachable",
            api,
        )

        self.assertIn(
            "checkConnection()",
            app,
        )

        self.assertIn(
            "Sprawdź połączenie",
            app,
        )


if __name__ == "__main__":
    unittest.main()
