import os
import tempfile
import unittest
import uuid

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from flip_core.auth_store import AuthStore

from backend.app.api.app import create_app
from backend.app.db.models import (
    User,
    Workspace,
    Membership,
    Listing,
)


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class Test56(unittest.TestCase):

    def test_http_workspace_and_deal(self):
        url = os.environ[
            "FLIP_BACKEND_TEST_DATABASE_URL"
        ]

        engine = create_engine(url)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth = AuthStore(root / "auth.sqlite")

            auth.init_db()
            user_id = auth.create_owner(
                "owner",
                "test-password-12345",
            )

            workspace = str(uuid.uuid4())
            forbidden_workspace = str(uuid.uuid4())
            listing = str(uuid.uuid4())

            with Session(engine) as db:
                with db.begin():
                    db.add(
                        User(
                            id=user_id,
                            username="pg-" + user_id,
                            password_hash="test-only",
                        )
                    )

                    db.add_all([
                        Workspace(
                            id=workspace,
                            name="Test workspace",
                        ),
                        Workspace(
                            id=forbidden_workspace,
                            name="Other workspace",
                        ),
                    ])

                    db.flush()

                    db.add(
                        Membership(
                            user_id=user_id,
                            workspace_id=workspace,
                            role="owner",
                        )
                    )

                    db.add(
                        Listing(
                            id=listing,
                            workspace_id=workspace,
                            source="MANUAL",
                            source_scope="test",
                            external_id=listing,
                            title="Test PC",
                        )
                    )

            env = {
                "FLIP_BACKEND_DATABASE_URL": url,
                "FLIP_API_AUTH_DB": str(
                    root / "auth.sqlite"
                ),
                "FLIP_API_DATA_ROOT": td,
                "FLIP_UNIVERSAL_DEV_DIR": td,
            }

            with patch.dict(os.environ, env):
                app = create_app()

                with TestClient(app) as api:
                    response = api.post(
                        "/api/v1/auth/login",
                        json={
                            "username": "owner",
                            "password": "test-password-12345",
                        },
                    )

                    self.assertEqual(
                        response.status_code,
                        200,
                        response.text,
                    )

                    headers = {
                        "Authorization": (
                            "Bearer "
                            + response.json()["access_token"]
                        ),
                        "Idempotency-Key": "purchase-0001",
                    }

                    path = (
                        f"/api/v2/workspaces/{workspace}"
                        "/deals"
                    )

                    body = {
                        "listing_id": listing,
                        "amount_minor": 100000,
                    }

                    self.assertEqual(
                        api.post(
                            path,
                            json=body,
                        ).status_code,
                        401,
                    )

                    denied = api.post(
                        f"/api/v2/workspaces/"
                        f"{forbidden_workspace}/deals",
                        headers=headers,
                        json=body,
                    )

                    self.assertEqual(
                        denied.status_code,
                        403,
                        denied.text,
                    )

                    first = api.post(
                        path,
                        headers=headers,
                        json=body,
                    )

                    self.assertEqual(
                        first.status_code,
                        200,
                        first.text,
                    )

                    repeat = api.post(
                        path,
                        headers=headers,
                        json=body,
                    )

                    self.assertEqual(
                        repeat.status_code,
                        200,
                        repeat.text,
                    )

                    self.assertEqual(
                        first.json(),
                        repeat.json(),
                    )

                    page = api.get(
                        path, headers=headers, params={"limit": 1}
                    )
                    self.assertEqual(page.status_code, 200, page.text)
                    self.assertEqual(len(page.json()["items"]), 1)
                    self.assertEqual(page.json()["items"][0]["status"], "BOUGHT")

                    deal_id = first.json()["deal_id"]
                    base = path + "/" + deal_id

                    cost_headers = {
                        **headers,
                        "Idempotency-Key": "cost-00001",
                    }

                    cost = api.post(
                        base + "/costs",
                        headers=cost_headers,
                        json={
                            "kind": "REPAIR",
                            "amount_minor": 15000,
                        },
                    )

                    self.assertEqual(
                        cost.status_code,
                        200,
                        cost.text,
                    )

                    costs_response = api.get(
                        base + "/costs", headers=headers
                    )
                    self.assertEqual(costs_response.status_code, 200)
                    self.assertEqual(
                        costs_response.json()["items"][0]["amount_minor"],
                        15000,
                    )

                    sale_headers = {
                        **headers,
                        "Idempotency-Key": "sale-00001",
                    }

                    sale = api.post(
                        base + "/sell",
                        headers=sale_headers,
                        json={
                            "amount_minor": 180000,
                        },
                    )

                    self.assertEqual(
                        sale.status_code,
                        200,
                        sale.text,
                    )

                    item = api.get(
                        base,
                        headers=headers,
                    )

                    self.assertEqual(
                        item.status_code,
                        200,
                        item.text,
                    )

                    self.assertEqual(
                        item.json()[
                            "realized_profit_minor"
                        ],
                        65000,
                    )

                    after_sale = api.get(path, headers=headers,
                                         params={"status": "SOLD", "limit": 1})
                    self.assertEqual(after_sale.status_code, 200)
                    self.assertEqual(len(after_sale.json()["items"]), 1)
                    self.assertEqual(after_sale.json()["items"][0]["id"], deal_id)

                    other_scope = api.get(
                        f"/api/v2/workspaces/{forbidden_workspace}/deals",
                        headers=headers,
                    )
                    self.assertEqual(other_scope.status_code, 403)

                    again = api.post(
                        base + "/sell",
                        headers={
                            **headers,
                            "Idempotency-Key": "sale-00002",
                        },
                        json={
                            "amount_minor": 180000,
                        },
                    )

                    self.assertEqual(
                        again.status_code,
                        409,
                    )

                app.state.backend_engine.dispose()

        engine.dispose()
