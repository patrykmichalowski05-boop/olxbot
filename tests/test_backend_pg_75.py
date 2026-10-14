import os
import tempfile
import unittest
import uuid

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

from flip_core.auth_store import AuthStore
from backend.app.api.app import create_app
from backend.app.db.models import (
    User,
    Workspace,
    Membership,
)


@unittest.skipUnless(
    os.getenv("FLIP_BACKEND_TEST_DATABASE_URL"),
    "requires disposable PostgreSQL",
)
class Test75(unittest.TestCase):

    def test_ingest_replay_and_isolation(self):
        raw_url = os.environ[
            "FLIP_BACKEND_TEST_DATABASE_URL"
        ]

        url = make_url(raw_url)

        if (
            url.host not in (
                "localhost",
                "127.0.0.1",
            )
            or url.database != "flip_test"
        ):
            raise RuntimeError(
                "Only test database allowed"
            )

        engine = create_engine(url)

        wid = str(uuid.uuid4())
        other = str(uuid.uuid4())

        try:
            with tempfile.TemporaryDirectory() as td:
                auth_path = Path(td) / "auth.db"

                auth = AuthStore(auth_path)
                auth.init_db()

                uid = auth.create_owner(
                    "owner",
                    "long-test-password-123",
                )

                with Session(engine) as db, db.begin():
                    db.add(
                        User(
                            id=uid,
                            username="radar-" + uid,
                            password_hash="test",
                        )
                    )

                    db.add_all([
                        Workspace(
                            id=wid,
                            name="radar",
                        ),
                        Workspace(
                            id=other,
                            name="other",
                        ),
                    ])

                    db.flush()

                    db.add(
                        Membership(
                            user_id=uid,
                            workspace_id=wid,
                            role="owner",
                        )
                    )

                env = {
                    "FLIP_BACKEND_DATABASE_URL": raw_url,
                    "FLIP_API_AUTH_DB": str(auth_path),
                    "FLIP_API_DATA_ROOT": td,
                    "FLIP_UNIVERSAL_DEV_DIR": td,
                }

                with patch.dict(os.environ, env):
                    app = create_app()

                    try:
                        with TestClient(app) as client:
                            login = client.post(
                                "/api/v1/auth/login",
                                json={
                                    "username": "owner",
                                    "password": "long-test-password-123",
                                },
                            )

                            self.assertEqual(
                                login.status_code,
                                200,
                                login.text,
                            )

                            bearer = {
                                "Authorization": (
                                    "Bearer "
                                    + login.json()["access_token"]
                                ),
                            }

                            base = (
                                f"/api/v2/workspaces/{wid}"
                                "/listings"
                            )

                            body = {
                                "source": "OLX",
                                "source_scope": "PL",
                                "external_id": (
                                    "test-" + str(uuid.uuid4())
                                ),
                                "title": "PC RTX 3070",
                                "price_minor": 120000,
                                "payload": {
                                    "url": "https://example.com/pc",
                                },
                            }

                            headers = {
                                **bearer,
                                "Idempotency-Key": "ingest-test-0001",
                            }

                            first = client.post(
                                base + "/ingest",
                                headers=headers,
                                json=body,
                            )

                            self.assertEqual(
                                first.status_code,
                                200,
                                first.text,
                            )

                            repeated = client.post(
                                base + "/ingest",
                                headers=headers,
                                json=body,
                            )

                            self.assertEqual(
                                repeated.json(),
                                first.json(),
                            )

                            self.assertEqual(
                                first.json()["revision"],
                                1,
                            )

                            headers["Idempotency-Key"] = (
                                "ingest-test-0002"
                            )

                            same = client.post(
                                base + "/ingest",
                                headers=headers,
                                json=body,
                            )

                            self.assertEqual(
                                same.status_code,
                                200,
                                same.text,
                            )

                            self.assertFalse(
                                same.json()["changed"]
                            )

                            headers["Idempotency-Key"] = (
                                "ingest-test-0003"
                            )

                            body["price_minor"] = 99000

                            changed = client.post(
                                base + "/ingest",
                                headers=headers,
                                json=body,
                            )

                            self.assertEqual(
                                changed.status_code,
                                200,
                                changed.text,
                            )

                            self.assertEqual(
                                changed.json()["revision"],
                                2,
                            )

                            radar = client.get(
                                base,
                                headers=bearer,
                            )

                            self.assertEqual(
                                radar.status_code,
                                200,
                                radar.text,
                            )

                            self.assertEqual(
                                len(radar.json()["items"]),
                                1,
                            )

                            self.assertEqual(
                                radar.json()["items"][0]["price_minor"],
                                99000,
                            )

                            other_base = (
                                f"/api/v2/workspaces/{other}"
                                "/listings"
                            )

                            denied = client.get(
                                other_base,
                                headers=bearer,
                            )

                            self.assertEqual(
                                denied.status_code,
                                403,
                            )

                            denied_write = client.post(
                                other_base + "/ingest",
                                headers=headers,
                                json=body,
                            )

                            self.assertEqual(
                                denied_write.status_code,
                                403,
                            )

                    finally:
                        app.state.backend_engine.dispose()

        finally:
            engine.dispose()
