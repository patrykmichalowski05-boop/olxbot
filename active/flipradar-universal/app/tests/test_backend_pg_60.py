import unittest
from backend.app.services.deals import deal_page

class Test60(unittest.TestCase):
    def test_bad_filters_rejected(self):
        with self.assertRaises(ValueError):
            deal_page(None, "workspace", status="DELETED")
        with self.assertRaises(ValueError):
            deal_page(None, "workspace", limit=True)
