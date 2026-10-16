import unittest

from backend.app.services.outbox_dispatch import (
    claim,
    SUPPORTED,
)


class Test68(unittest.TestCase):

    def test_claim_validation(self):
        for limit in (0, 101, True):
            with self.assertRaises(ValueError):
                claim(None, limit=limit)

        with self.assertRaises(ValueError):
            claim(None, lease_seconds=1)

    def test_supported_events(self):
        self.assertIn(
            "DEAL_COST_ADDED",
            SUPPORTED,
        )
