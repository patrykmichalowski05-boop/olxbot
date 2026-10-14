import os
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Workspace,
    Listing,
    Deal,
    DealCost,
)
from backend.app.services.deals import deal_page, summary


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class TestFinancialGuiContract(unittest.TestCase):

    def test_page_and_detail_finances(self):
        url = make_url(
            os.environ["FLIP_BACKEND_TEST_DATABASE_URL"]
        )

        if (
            url.host not in ("localhost", "127.0.0.1")
            or url.database != "flip_test"
        ):
            raise RuntimeError("Disposable PostgreSQL only")

        engine = create_engine(url)

        ids = [
            str(uuid.uuid4())
            for _ in range(8)
        ]

        ws, other, lid1, lid2, did1, did2, cid1, cid2 = ids

        try:
            with Session(engine) as db, db.begin():
                db.add_all([
                    Workspace(id=ws, name="gui-contract"),
                    Workspace(id=other, name="other-contract"),
                ])

                db.flush()

                db.add_all([
                    Listing(
                        id=lid1,
                        workspace_id=ws,
                        source="MANUAL",
                        source_scope="ci",
                        external_id=lid1,
                        title="PC RTX",
                    ),
                    Listing(
                        id=lid2,
                        workspace_id=ws,
                        source="MANUAL",
                        source_scope="ci",
                        external_id=lid2,
                        title="Laptop",
                    ),
                ])

                db.flush()

                db.add_all([
                    Deal(
                        id=did1,
                        workspace_id=ws,
                        listing_id=lid1,
                        status="SOLD",
                        purchase_minor=150000,
                        sale_minor=200000,
                        currency="PLN",
                    ),
                    Deal(
                        id=did2,
                        workspace_id=ws,
                        listing_id=lid2,
                        status="BOUGHT",
                        purchase_minor=80000,
                        sale_minor=None,
                        currency="PLN",
                    ),
                ])

                db.flush()

                db.add_all([
                    DealCost(
                        id=cid1,
                        deal_id=did1,
                        kind="prep",
                        amount_minor=10000,
                    ),
                    DealCost(
                        id=cid2,
                        deal_id=did1,
                        kind="shipping",
                        amount_minor=5000,
                    ),
                ])

            with Session(engine) as db:
                page = deal_page(db, ws, limit=20)

                by_id = {
                    x["id"]: x
                    for x in page["items"]
                }

                self.assertEqual(len(by_id), 2)
                self.assertEqual(
                    by_id[did1]["title"], "PC RTX"
                )
                self.assertEqual(
                    by_id[did1]["cost_minor"], 15000
                )
                self.assertEqual(
                    by_id[did1]["realized_profit_minor"],
                    35000,
                )
                self.assertEqual(
                    by_id[did2]["cost_minor"], 0
                )
                self.assertIsNone(
                    by_id[did2]["realized_profit_minor"]
                )

                detail = summary(db, ws, did1)

                self.assertEqual(detail["id"], did1)
                self.assertEqual(
                    detail["title"], "PC RTX"
                )
                self.assertEqual(
                    detail["realized_profit_minor"],
                    35000,
                )
                self.assertEqual(
                    detail["cost_minor"], 15000
                )

                self.assertEqual(
                    deal_page(db, other)["items"], []
                )
                self.assertIsNone(
                    summary(db, other, did1)
                )
        finally:
            engine.dispose()
