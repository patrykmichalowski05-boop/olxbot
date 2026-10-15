import os
import tempfile
import unittest
from unittest.mock import patch
import telegram_notifier as tg


class TestWatchReview(unittest.TestCase):
    def test_watch_notification_once(self):
        details = {
            'title': 'RTX 5060 Ti',
            'price': 3200,
            'cpu': 'i5-14400F',
            'gpu': 'RTX 5060 TI',
        }
        valuation = {'profit': 474, 'confidence': 'LOW'}
        url = 'https://www.olx.pl/d/oferta/test-ID1cLNZr.html'

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'WATCH_REVIEW_DB': tmp + '/watch.db'}), \
                 patch.object(tg, 'calculate_deal_score', return_value={'score': 60}), \
                 patch.object(tg, 'negotiation_values', return_value={}), \
                 patch.object(tg, 'calculate_action', return_value={'action': 'WATCH'}), \
                 patch.object(tg, 'upsert_watch'), \
                 patch.object(tg, 'save_snapshot'), \
                 patch.object(tg, 'send_message', return_value=True) as sender:

                for _ in range(2):
                    status = tg.send_flip_alert(
                        details, valuation, 'POLSKA', url, return_status=True
                    )
                    self.assertEqual(status, 'SUPPRESSED')
                sender.assert_called_once()


if __name__ == '__main__':
    unittest.main()
