import unittest

from universal_v2.mobile_radar_routes import normalize


class Test37(unittest.TestCase):

    def test_mobile_contract(self):
        result = normalize({
            'items': [{
                'id': 7,
                'source': 'MANUAL',
                'title': 'RTX 3070',
                'decision': 'NO_RELIABLE_VALUATION',
                'analysis': {'reason': 'NO_MARKET'},
            }],
            'next_before_id': None,
        })

        row = result['items'][0]

        self.assertEqual(row['snapshot_id'], 7)
        self.assertEqual(row['platform'], 'MANUAL')
        self.assertIsNone(row['price_minor'])
        self.assertIsNone(row['url'])

    def test_empty_page(self):
        result = normalize({
            'items': [],
            'next_before_id': None
        })
        self.assertEqual(result['items'], [])
