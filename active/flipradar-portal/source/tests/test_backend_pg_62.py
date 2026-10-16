import os
import uuid
import unittest

from sqlalchemy import (
    create_engine,
    ForeignKeyConstraint,
)

from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Deal,
    Listing,
    Workspace,
)


class Test62(unittest.TestCase):

    def test_composite_foreign_key(self):
        self.assertTrue(
            any(
                isinstance(c, ForeignKeyConstraint)
                and c.name == "fk_deals_workspace_listing"
                for c in Deal.__table__.constraints
            )
        )

        self.assertTrue(
            any(
                c.name == "uq_listings_ws_id"
                for c in Listing.__table__.constraints
            )
        )

    @unittest.skipUnless(
        os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
        "requires disposable PostgreSQL",
    )
    def test_cross_workspace_deal_rejected(self):
        url = make_url(
            os.environ["FLIP_BACKEND_TEST_DATABASE_URL"]
        )

        if (
            url.host not in ("localhost", "127.0.0.1")
            or url.database != "flip_test"
        ):
            raise RuntimeError(
                "Only local disposable database permitted"
            )

        engine = create_engine(url)

        w1, w2, lid = (
            str(uuid.uuid4())
            for _ in range(3)
        )

        try:
            with Session(engine) as db, db.begin():
                db.add_all([
                    Workspace(id=w1, name="one"),
                    Workspace(id=w2, name="two"),
                ])

                db.flush()

                db.add(
                    Listing(
                        id=lid,
                        workspace_id=w1,
                        source="MANUAL",
                        source_scope="test",
                        external_id=lid,
                        title="PC",
                    )
                )

            with self.assertRaises(IntegrityError):
                with Session(engine) as db, db.begin():
                    db.add(
                        Deal(
                            id=str(uuid.uuid4()),
                            workspace_id=w2,
                            listing_id=lid,
                            status="BOUGHT",
                            purchase_minor=100,
                            sale_minor=None,
                            currency="PLN",
                        )
                    )

                    db.flush()

        finally:
            engine.dispose()
