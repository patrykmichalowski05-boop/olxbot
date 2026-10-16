import copy
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from deal_action import calculate_action
import telegram_notifier as tg


FIXTURE = Path(__file__).parent / "fixtures" / "hot_watch_asus.json"


class TestHotWatchAlert(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(FIXTURE.read_text())

    def action(self, details=None, valuation=None):
        details = details if details is not None else self.case["details"]
        valuation = valuation if valuation is not None else self.case["valuation"]

        return calculate_action(
            details=details,
            valuation=valuation,
            score=64,
        )["action"]

    def test_asus_hot_becomes_review(self):
        self.assertEqual(self.action(), "REVIEW")

    def test_bad_condition_stays_skip(self):
        v = copy.deepcopy(self.case["valuation"])
        v["ai_condition"] = "bad"
        self.assertEqual(self.action(valuation=v), "SKIP")

    def test_low_profit_not_hot_review(self):
        v = copy.deepcopy(self.case["valuation"])
        v["profit"] = 200
        v["hot"] = False
        self.assertNotIn(
            self.action(valuation=v),
            ("BUY_NOW", "BUY", "REVIEW"),
        )

    def test_missing_cpu_not_hot_review(self):
        d = copy.deepcopy(self.case["details"])
        d["cpu"] = None
        self.assertNotIn(
            self.action(details=d),
            ("BUY_NOW", "BUY", "REVIEW"),
        )

    def test_telegram_send_path_offline(self):
        case = self.case

        with (
            patch.object(
                socket.socket,
                "connect",
                side_effect=RuntimeError("Network disabled"),
            ),
            patch.object(tg, "send_message", return_value=True) as send,
            patch.object(tg, "already_sent", return_value=False),
            patch.object(tg, "record_alert") as record,
            patch.object(tg, "save_snapshot"),
            patch.object(tg, "upsert_watch"),
            patch.object(tg, "promote_if_watched"),
        ):
            status = tg.send_flip_alert(
                case["details"],
                case["valuation"],
                case["mode"],
                case["url"],
                return_status=True,
            )

            self.assertEqual(status, "SENT")
            send.assert_called_once()
            record.assert_called_once()

            message = send.call_args.args[0]
            self.assertIn("PILNA WERYFIKACJA", message)
            self.assertIn("285", message)
            self.assertIn("ID1cHh6a", message)


if __name__ == "__main__":
    unittest.main()
