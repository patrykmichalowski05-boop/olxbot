import unittest

from backend.app.services.deals import deal_events


class Test64(unittest.TestCase):

    def test_audit_contract(self):
        self.assertTrue(
            callable(deal_events)
        )
