import unittest

from backend.app.db.models import Listing
from backend.app.services.listing_radar import page


class Test74(unittest.TestCase):

    def test_chronology(self):
        self.assertIsNotNone(
            Listing.__table__
            .c.created_at.server_default
        )

        self.assertIn(
            "ix_listings_ws_created_id",
            {
                i.name
                for i in Listing.__table__.indexes
            },
        )

    def test_filters(self):
        for kwargs in (
            {"limit": True},
            {"limit": 51},
            {"q": "x" * 121},
        ):
            with self.assertRaises(ValueError):
                page(
                    None,
                    "workspace",
                    **kwargs,
                )
