import os
import uuid
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import (
    Workspace,
    OutboxEvent,
    NotificationInbox,
)

from backend.app.services.outbox_dispatch import (
    process_batch,
    MAX_ATTEMPTS,
)


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class Test71(unittest.TestCase):

    def test_delivery_and_deduplication(self):
        url = make_url(
            os.environ[
                "FLIP_BACKEND_TEST_DATABASE_URL"
            ]
        )

        if (
            url.host not in (
                "localhost",
                "127.0.0.1",
            )
            or url.database != "flip_test"
        ):
            raise RuntimeError(
                "Disposable test database required"
            )

        engine = create_engine(url)

        factory = sessionmaker(
            engine,
            expire_on_commit=False,
        )

        workspace_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())
        bad_id = str(uuid.uuid4())

        try:
            with Session(engine) as db, db.begin():
                db.add(
                    Workspace(
                        id=workspace_id,
                        name="outbox-ci",
                    )
                )

                db.flush()

                db.add_all([
                    OutboxEvent(
                        id=event_id,
                        workspace_id=workspace_id,
                        event_type="DEAL_PURCHASED",
                        payload={"deal_id": "x"},
                    ),
                    OutboxEvent(
                        id=bad_id,
                        workspace_id=workspace_id,
                        event_type="UNKNOWN_EVENT",
                        payload={"deal_id": "y"},
                    ),
                ])

            result = process_batch(
                factory,
                limit=100,
            )

            self.assertGreaterEqual(
                result["delivered"],
                1,
            )

            with Session(engine) as db:
                notification = db.scalar(
                    select(NotificationInbox).where(
                        NotificationInbox.source_event_id
                        == event_id
                    )
                )

                self.assertIsNotNone(
                    notification
                )

                self.assertEqual(
                    db.get(
                        OutboxEvent,
                        event_id,
                    ).status,
                    "DELIVERED",
                )

                self.assertEqual(
                    db.get(
                        OutboxEvent,
                        bad_id,
                    ).status,
                    "DEAD",
                )

                copies = db.scalars(
                    select(NotificationInbox).where(
                        NotificationInbox.source_event_id
                        == event_id
                    )
                ).all()

                self.assertEqual(
                    len(copies),
                    1,
                )

            self.assertEqual(
                MAX_ATTEMPTS,
                5,
            )

        finally:
            engine.dispose()


class Test71Config(unittest.TestCase):

    def test_celery_registration(self):
        from backend.app.services.celery_tasks import (
            app,
        )

        self.assertIn(
            "flip_hunter.outbox.poll",
            app.tasks,
        )
