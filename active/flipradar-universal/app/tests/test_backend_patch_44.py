import unittest

from universal_v2.mobile_radar_routes import normalize


class MobileRadarContractTest(unittest.TestCase):

    def test_offered_price_not_invented_valuation(self):
        item = {
            'id': 15,
            'title': 'PC',
            'source': 'MANUAL',
            'decision': 'NO_RELIABLE_VALUATION',
            'analysis': {
                'decision': 'NO_RELIABLE_VALUATION'
            },
            'price_minor': 99000,
            'url': None,
            'observed_at': '2026-10-14T08:00:00+00:00'
        }

        page = normalize({
            'items': [item],
            'next_before_id': None
        })

        self.assertEqual(
            page['items'][0]['price_minor'],
            99000
        )

        self.assertEqual(
            page['items'][0]['decision'],
            'NO_RELIABLE_VALUATION'
        )

        self.assertEqual(
            page['items'][0]['observed_at'],
            item['observed_at']
        )

        self.assertIsNone(
            page['items'][0]['url']
        )
