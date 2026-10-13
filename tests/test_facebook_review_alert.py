import ast
import unittest
from pathlib import Path

from facebook.facebook_review_notifier import (
    send_watch_review_alert,
)

URL = (
    "https://www.facebook.com/"
    "marketplace/item/1726069351826337/"
)

DETAILS = {
    "price": 1100,
    "title": "PC Ryzen 5 3600 RTX 2060 SUPER 16 GB",
    "cpu": "Ryzen 5 3600",
    "gpu": "RTX 2060 SUPER",
    "ram": 16,
}

META = {
    "price": 1100,
    "currency": "PLN",
    "is_live": True,
    "is_sold": False,
}

SPECS = {
    "cpu": "Ryzen 5 3600",
    "gpu": "RTX 2060 SUPER",
    "ram": 16,
}

VALUATION = {
    "quick_sale": 1862,
    "total_cost": 1200,
    "profit": 662,
    "confidence": "FALLBACK",
    "ai_issues": [],
}


class ReviewTests(unittest.TestCase):

    def check(
        self,
        action="WATCH",
        details=None,
        metadata=None,
        specs=None,
        valuation=None,
        url=URL,
        min_profit=250,
        send_ok=True,
        prior=False,
    ):
        events = []

        def send(message):
            events.append(("send", message))
            return send_ok

        def already(details, url):
            events.append(("dedupe", url))
            return prior

        def record(**kwargs):
            events.append(("record", kwargs))

        result = send_watch_review_alert(
            details if details is not None else DETAILS,
            metadata if metadata is not None else META,
            specs if specs is not None else SPECS,
            valuation if valuation is not None else VALUATION,
            url,
            action,
            62,
            min_profit,
            send_fn=send,
            already_sent_fn=already,
            record_fn=record,
        )

        return result, events

    def test_watch_sends_review(self):
        result, events = self.check()

        self.assertEqual(result, "SENT")
        self.assertEqual(
            [item[0] for item in events],
            ["dedupe", "send", "record"],
        )
        self.assertIn(
            "RĘCZNEJ WERYFIKACJI",
            events[1][1],
        )

    def test_duplicate_suppressed(self):
        result, events = self.check(prior=True)

        self.assertEqual(result, "SUPPRESSED")
        self.assertEqual(len(events), 1)

    def test_send_failure(self):
        result, events = self.check(send_ok=False)

        self.assertEqual(result, "ERROR")
        self.assertEqual(
            [x[0] for x in events],
            ["dedupe", "send"],
        )

    def test_skip_does_not_send(self):
        result, events = self.check(action="SKIP")

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_review_keeps_existing_path(self):
        result, events = self.check(action="REVIEW")

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_profit_below_400(self):
        result, events = self.check(
            valuation={
                **VALUATION,
                "profit": 300,
                "quick_sale": 1500,
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_risky_condition(self):
        result, events = self.check(
            valuation={
                **VALUATION,
                "ai_condition": "risky",
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_higher_configured_threshold(self):
        result, events = self.check(min_profit=700)

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_invalid_url(self):
        result, events = self.check(
            url=(
                "https://facebook.com.evil.example/"
                "marketplace/item/123"
            )
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_unknown_currency(self):
        result, events = self.check(
            metadata={
                **META,
                "currency": None,
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_unconfirmed_availability(self):
        result, events = self.check(
            metadata={
                **META,
                "is_live": None,
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_inconsistent_valuation(self):
        result, events = self.check(
            valuation={
                **VALUATION,
                "profit": 999,
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_insufficient_ram(self):
        result, events = self.check(
            specs={
                **SPECS,
                "ram": 8,
            }
        )

        self.assertEqual(result, "NOT_ELIGIBLE")
        self.assertFalse(events)

    def test_facebook_scanner_integration(self):
        root = Path(__file__).resolve().parents[1]
        source = (
            root / "facebook/facebook_flip_scanner.py"
        ).read_text(encoding="utf-8")

        tree = ast.parse(source)

        wrapper = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "send_facebook_flip_alert"
        )

        calls = {
            node.func.id
            for node in ast.walk(wrapper)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }

        self.assertIn(
            "send_watch_review_alert",
            calls,
        )
        self.assertIn("send_flip_alert", calls)


if __name__ == "__main__":
    unittest.main()
