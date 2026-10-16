import os
import uuid
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import Workspace, OutboxEvent, NotificationInbox
from backend.app.services.outbox_dispatch import claim, fail, materialize
from backend.app.services.notification_inbox import page


@unittest.skipUnless(
    os.getenv('FLIP_BACKEND_TEST_DATABASE_URL'),
    'requires disposable PostgreSQL',
)
class Test72(unittest.TestCase):
    def test_lease_fencing_retry_and_inbox_isolation(self):
        url = make_url(os.environ['FLIP_BACKEND_TEST_DATABASE_URL'])

        if url.host not in ('localhost', '127.0.0.1') or url.database != 'flip_test':
            raise RuntimeError('Only disposable flip_test PostgreSQL permitted')

        engine = create_engine(url)
        factory = sessionmaker(engine, expire_on_commit=False)
        workspace_id = str(uuid.uuid4())
        other_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        try:
            with Session(engine) as db, db.begin():
                db.add_all([
                    Workspace(id=workspace_id, name='lease-test'),
                    Workspace(id=other_id, name='other-workspace'),
                ])
                db.flush()
                db.add(OutboxEvent(
                    id=event_id,
                    workspace_id=workspace_id,
                    event_type='DEAL_PURCHASED',
                    payload={'deal_id': str(uuid.uuid4())},
                ))

            with factory() as db:
                tickets = claim(db, limit=100)

            matches = [token for eid, token in tickets if eid == event_id]
            self.assertEqual(len(matches), 1)
            old_token = matches[0]

            with factory() as db:
                self.assertFalse(materialize(db, event_id, 'invalid-lease-token'))

            with factory() as db:
                self.assertTrue(fail(
                    db, event_id, old_token,
                    reason='PROCESSING_FAILED',
                ))

            with factory() as db:
                record = db.get(OutboxEvent, event_id)
                self.assertEqual(record.status, 'PENDING')
                self.assertEqual(record.attempts, 1)

            with Session(engine) as db, db.begin():
                db.get(OutboxEvent, event_id).available_at = (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                )

            with factory() as db:
                tickets = claim(db, limit=100)

            fresh = [token for eid, token in tickets if eid == event_id]
            self.assertEqual(len(fresh), 1)
            self.assertNotEqual(fresh[0], old_token)

            with factory() as db:
                self.assertFalse(materialize(db, event_id, old_token))

            with factory() as db:
                self.assertTrue(materialize(db, event_id, fresh[0]))

            with factory() as db:
                self.assertFalse(materialize(db, event_id, fresh[0]))

            with Session(engine) as db:
                rows = db.scalars(
                    select(NotificationInbox).where(
                        NotificationInbox.source_event_id == event_id
                    )
                ).all()

                self.assertEqual(len(rows), 1)
                self.assertEqual(len(page(db, workspace_id)['items']), 1)
                self.assertEqual(len(page(db, other_id)['items']), 0)
                self.assertEqual(
                    db.get(OutboxEvent, event_id).status,
                    'DELIVERED',
                )
        finally:
            engine.dispose()
