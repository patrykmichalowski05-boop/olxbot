import unittest

from backend.app.db.models import (
    Base,
    OutboxEvent,
    NotificationInbox,
)


class Test67(unittest.TestCase):

    def test_outbox_and_inbox_schema(self):
        self.assertIn(
            "notification_inbox",
            Base.metadata.tables,
        )

        for name in (
            "status",
            "attempts",
            "lease_until",
            "lease_token",
            "available_at",
        ):
            self.assertIn(
                name,
                OutboxEvent.__table__.c,
            )

        self.assertTrue(
            NotificationInbox.__table__
            .c.source_event_id.unique
        )
