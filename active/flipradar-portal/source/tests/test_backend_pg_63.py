import inspect
import unittest

from backend.app.db.models import OutboxEvent
from backend.app.services.deals import (
    purchase,
    add_cost,
    sell,
)


class Test63(unittest.TestCase):

    def test_outbox_actor_and_time(self):
        table = OutboxEvent.__table__

        self.assertIn(
            "actor_user_id",
            table.c,
        )

        self.assertIsNotNone(
            table.c.created_at.server_default,
        )

        for operation in (
            purchase,
            add_cost,
            sell,
        ):
            self.assertIn(
                "actor_id",
                inspect.signature(operation).parameters,
            )
