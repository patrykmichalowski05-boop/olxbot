import unittest
from backend.app.services.outbox_dispatch import SUPPORTED

class Test76(unittest.TestCase):
    def test_price_drop_supported(self):
        self.assertIn('LISTING_PRICE_DROP', SUPPORTED)
        self.assertIn('DEAL_PURCHASED', SUPPORTED)
