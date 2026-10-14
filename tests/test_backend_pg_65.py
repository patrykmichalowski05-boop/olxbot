import os
import uuid
import unittest

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

from backend.app.db.models import (
    User,
    Workspace,
    Listing,
)

from backend.app.services.deals import (
    purchase,
    sell,
    DealConflict,
)


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class Test65(unittest.TestCase):

    def test_concurrent_purchase_and_sale(self):
        url = make_url(
            os.environ["FLIP_BACKEND_TEST_DATABASE_URL"]
        )

        if (
            url.host not in ("localhost", "127.0.0.1")
            or url.database != "flip_test"
        ):
            raise RuntimeError(
                "Only disposable localhost database allowed"
            )

        engine = create_engine(
            url,
            pool_size=3,
            max_overflow=0,
        )

        uid, wid, lid = (
            str(uuid.uuid4())
            for _ in range(3)
        )

        try:
            with Session(engine) as db, db.begin():
                db.add(
                    User(
                        id=uid,
                        username="race-" + uid,
                        password_hash="test",
                    )
                )

                db.add(
                    Workspace(
                        id=wid,
                        name="race-test",
                    )
                )

                db.flush()

                db.add(
                    Listing(
                        id=lid,
                        workspace_id=wid,
                        source="MANUAL",
                        source_scope="test",
                        external_id=lid,
                        title="Concurrent PC",
                    )
                )

            def buy(n):
                with Session(engine) as db:
                    try:
                        return (
                            "OK",
                            purchase(
                                db,
                                wid,
                                lid,
                                100000,
                                f"buy-race-{n:02d}",
                            ),
                        )

                    except DealConflict:
                        return "CONFLICT", None

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(buy, (1, 2))
                )

            self.assertEqual(
                [r[0] for r in results].count("OK"),
                1,
                results,
            )

            self.assertEqual(
                [r[0] for r in results].count("CONFLICT"),
                1,
                results,
            )

            deal_id = next(
                r[1]["deal_id"]
                for r in results
                if r[0] == "OK"
            )

            def do_sell(n):
                with Session(engine) as db:
                    try:
                        sell(
                            db,
                            wid,
                            deal_id,
                            180000,
                            f"sale-race-{n:02d}",
                        )

                        return "OK"

                    except DealConflict:
                        return "CONFLICT"

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(do_sell, (1, 2))
                )

            self.assertCountEqual(
                results,
                ["OK", "CONFLICT"],
            )

        finally:
            engine.dispose()
