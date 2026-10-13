import os
import sqlite3

from .auth_store import AuthStore
from .listing_repository import LegacyListingReader
from .policy import FlipPolicy
from .profit_engine import quote


def create_app():
    from fastapi import (
        Depends,
        FastAPI,
        Header,
        HTTPException,
        Query,
    )
    from pydantic import (
        BaseModel,
        Field,
        StrictInt,
    )

    auth_path = os.getenv("FLIP_API_AUTH_DB")
    data_path = os.getenv("FLIP_API_DATA_ROOT")

    if not auth_path or not data_path:
        raise RuntimeError(
            "Ustaw FLIP_API_AUTH_DB "
            "i FLIP_API_DATA_ROOT"
        )

    auth = AuthStore(auth_path)
    auth.init_db()

    reader = LegacyListingReader(data_path)

    app = FastAPI(
        title="Flip Hunter Mobile Dev",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    class Credentials(BaseModel):
        username: str = Field(
            min_length=3,
            max_length=60,
        )
        password: str = Field(
            min_length=1,
            max_length=512,
        )

    class RefreshPayload(BaseModel):
        refresh_token: str = Field(
            min_length=32,
            max_length=256,
        )

    class PreviewPayload(BaseModel):
        purchase_minor: StrictInt
        sale_minor: StrictInt
        costs: dict[str, StrictInt] = Field(
            default_factory=dict
        )
        confidence: str = "LOW"
        condition: str = "unknown"

    def user(
        authorization: str | None = Header(
            default=None
        )
    ):
        parts = (
            authorization or ""
        ).split(" ", 1)

        if (
            len(parts) != 2
            or parts[0].lower() != "bearer"
        ):
            raise HTTPException(
                401, "Unauthorized"
            )

        try:
            return auth.verify_access(parts[1])

        except ValueError:
            raise HTTPException(
                401, "Unauthorized"
            ) from None

    @app.post("/api/v1/auth/login")
    def login(data: Credentials):
        try:
            return auth.login(
                data.username,
                data.password,
            )
        except ValueError:
            raise HTTPException(
                401, "Invalid credentials"
            ) from None

    @app.post("/api/v1/auth/refresh")
    def refresh(data: RefreshPayload):
        try:
            return auth.refresh(
                data.refresh_token
            )
        except ValueError:
            raise HTTPException(
                401, "Invalid refresh token"
            ) from None

    @app.post("/api/v1/auth/logout")
    def logout(
        authorization: str | None = Header(
            default=None
        ),
        _=Depends(user),
    ):
        auth.logout(
            authorization.split(" ", 1)[1]
        )

        return {"ok": True}

    @app.get("/api/v1/me")
    def me(user_id=Depends(user)):
        return {
            "user_id": user_id,
            "access": "single_owner_dev",
        }

    @app.get("/api/v1/listings")
    def listings(
        limit: int = Query(
            default=20, ge=1, le=100
        ),
        before_id: int | None = Query(
            default=None, gt=0
        ),
        q: str = Query(
            default="", max_length=120
        ),
        _=Depends(user),
    ):
        try:
            items = reader.list(
                limit=limit,
                before_id=before_id,
                q=q,
            )

        except (sqlite3.Error, FileNotFoundError):
            raise HTTPException(
                503, "Database unavailable"
            ) from None

        return {
            "items": items,
            "next_before_id": (
                items[-1]["id"]
                if len(items) == limit
                else None
            ),
        }

    @app.get("/api/v1/listings/{listing_id}")
    def detail(
        listing_id: int,
        _=Depends(user),
    ):
        try:
            item = reader.get(listing_id)
        except (sqlite3.Error, FileNotFoundError):
            raise HTTPException(
                503, "Database unavailable"
            ) from None

        if item is None:
            raise HTTPException(
                404, "Listing not found"
            )

        return item

    @app.get(
        "/api/v1/listings/{listing_id}/history"
    )
    def history(
        listing_id: int,
        _=Depends(user),
    ):
        try:
            items = reader.history(listing_id)
        except (sqlite3.Error, FileNotFoundError):
            raise HTTPException(
                503, "Database unavailable"
            ) from None

        if items is None:
            raise HTTPException(
                404, "Listing not found"
            )

        return {"items": items}

    @app.post("/api/v1/valuations/preview")
    def preview(
        data: PreviewPayload,
        _=Depends(user),
    ):
        try:
            return quote(
                data.purchase_minor,
                data.sale_minor,
                data.costs,
                FlipPolicy(),
                confidence=data.confidence,
                condition=data.condition,
            )

        except ValueError as exc:
            raise HTTPException(
                422, str(exc)
            ) from exc


    @app.get("/api/v1/radar")
    def radar(
        limit: int = Query(default=20, ge=1, le=100),
        before_id: int | None = Query(default=None, gt=0),
        q: str = Query(default="", max_length=120),
        _=Depends(user),
    ):
        from .radar_repository import SnapshotRadar

        try:
            items = SnapshotRadar(data_path).list(
                limit=limit,
                before_id=before_id,
                q=q,
            )
        except (sqlite3.Error, FileNotFoundError):
            raise HTTPException(
                503,
                "Radar database unavailable",
            ) from None

        return {
            "items": items,
            "next_before_id": (
                items[-1]["snapshot_id"]
                if len(items) == limit
                else None
            ),
        }

    return app
