import unittest

from sqlalchemy import UniqueConstraint
from backend.app.db.models import Base


class Test48(unittest.TestCase):

    def test_foundation_schema(self):
        self.assertEqual(
            set(Base.metadata.tables),
            {
                "users",
                "workspaces",
                "memberships",
                "listings",
                "listing_observations",
                "valuation_runs",
                "deals",
                "deal_costs",
                "outbox_events",
                "idempotency_records",
            },
        )

    def test_scope_constraint(self):
        listing = Base.metadata.tables["listings"]

        self.assertTrue(
            any(
                c.name == "uq_listing_scope"
                for c in listing.constraints
                if isinstance(c, UniqueConstraint)
            )
        )
