import os
import uuid
import unittest

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Base,
    User,
    Workspace,
    Membership,
    Listing,
    OutboxEvent,
)
from backend.app.services.deals import (
    purchase,
    add_cost,
    sell,
    summary,
    DealConflict,
)


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class PostgresIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        url = make_url(
            os.environ[
                "FLIP_BACKEND_TEST_DATABASE_URL"
            ]
        )

        if (
            url.host not in (
                "127.0.0.1",
                "localhost",
            )
            or url.database != "flip_test"
        ):
            raise RuntimeError(
                "Only local flip_test database permitted"
            )

        cls.engine = create_engine(url)

        existing = set(
            inspect(cls.engine).get_table_names()
        )

        assert set(Base.metadata.tables) <= existing, (
            "Run Alembic upgrade head on test DB first"
        )

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_ledger_and_idempotency(self):
        uid, wid, lid = [
            str(uuid.uuid4()) for _ in range(3)
        ]

        with Session(self.engine) as session:
            with session.begin():
                session.add(
                    User(
                        id=uid,
                        username="tester-" + uid,
                        password_hash="hash",
                    )
                )
                session.add(
                    Workspace(
                        id=wid,
                        name="test",
                    )
                )

                session.flush()

                session.add(
                    Membership(
                        user_id=uid,
                        workspace_id=wid,
                        role="owner",
                    )
                )

                session.add(
                    Listing(
                        id=lid,
                        workspace_id=wid,
                        source="MANUAL",
                        source_scope="test",
                        external_id=lid,
                        title="Test PC",
                    )
                )

        with Session(self.engine) as session:
            first = purchase(
                session, wid, lid,
                100000, "purchase-1",
            )

        with Session(self.engine) as session:
            repeat = purchase(
                session, wid, lid,
                100000, "purchase-1",
            )

        self.assertEqual(first, repeat)
        deal_id = first["deal_id"]

        with Session(self.engine) as session:
            with self.assertRaises(DealConflict):
                purchase(
                    session, wid, lid,
                    99999, "purchase-1",
                )

        with Session(self.engine) as session:
            add_cost(
                session, wid, deal_id,
                "REPAIR", 15000, "repair-01",
            )

        with Session(self.engine) as session:
            sell(
                session, wid, deal_id,
                180000, "sell-0001",
            )

        with Session(self.engine) as session:
            result = summary(
                session, wid, deal_id
            )

            self.assertEqual(
                result["realized_profit_minor"],
                65000,
            )

        with Session(self.engine) as session:
            add_cost(
                session, wid, deal_id,
                "FEE", 5000, "fee-0001",
            )

        with Session(self.engine) as session:
            result = summary(
                session, wid, deal_id
            )

            self.assertEqual(
                result["realized_profit_minor"],
                60000,
            )

            self.assertIsNone(
                summary(session, "other", deal_id)
            )

            event = session.scalar(
                select(OutboxEvent)
                .where(
                    OutboxEvent.workspace_id == wid
                )
                .limit(1)
            )

            self.assertEqual(
                event.event_type,
                "DEAL_PURCHASED",
            )
