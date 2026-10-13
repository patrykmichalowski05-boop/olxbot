"""Internal development API. Never expose without real user auth."""

import os
import secrets
import sqlite3
from pathlib import Path

from .listing_repository import LegacyListingReader
from .profit_engine import quote
from .policy import FlipPolicy


def create_app():
    from fastapi import (
        Depends,
        FastAPI,
        Header,
        HTTPException,
        Query,
    )

    key = os.environ.get("FLIP_API_KEY", "")

    if len(key) < 32:
        raise RuntimeError(
            "FLIP_API_KEY must have at least 32 characters"
        )

    data_root = Path(
        os.environ.get(
            "FLIP_API_DATA_ROOT",
            str(Path(__file__).resolve().parents[1]),
        )
    )

    reader = LegacyListingReader(data_root)

    app = FastAPI(
        title="Flip Hunter Internal API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def authorized(
        x_admin_api_key: str | None = Header(
            default=None,
            alias="X-Admin-Api-Key",
        )
    ):
        if (
            not x_admin_api_key
            or not secrets.compare_digest(
                x_admin_api_key,
                key,
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
            )

    def database_error(exc):
        raise HTTPException(
            status_code=503,
            detail="Listing database unavailable",
        ) from exc

    @app.get("/api/v1/health")
    def health(_=Depends(authorized)):
        return {
            "status": "ok",
            "mode": "internal_read_only",
            "version": "0.1.0",
        }

    @app.get("/api/v1/listings")
    def listings(
        limit: int = Query(default=20, ge=1, le=100),
        before_id: int | None = Query(default=None, gt=0),
        q: str = Query(default="", max_length=120),
        _=Depends(authorized),
    ):
        try:
            items = reader.list(
                limit=limit,
                before_id=before_id,
                q=q,
            )
        except (sqlite3.Error, FileNotFoundError) as exc:
            database_error(exc)

        return {
            "items": items,
            "next_before_id": (
                items[-1]["id"] if len(items) == limit
                else None
            ),
        }

    @app.get("/api/v1/listings/{listing_id}")
    def detail(
        listing_id: int,
        _=Depends(authorized),
    ):
        try:
            item = reader.get(listing_id)
        except (sqlite3.Error, FileNotFoundError) as exc:
            database_error(exc)

        if item is None:
            raise HTTPException(404, "Listing not found")

        return item

    @app.get("/api/v1/listings/{listing_id}/history")
    def history(
        listing_id: int,
        _=Depends(authorized),
    ):
        try:
            items = reader.history(listing_id)
        except (sqlite3.Error, FileNotFoundError) as exc:
            database_error(exc)

        if items is None:
            raise HTTPException(404, "Listing not found")

        return {"items": items}

    @app.post("/api/v1/valuations/preview")
    def preview(
        payload: dict,
        _=Depends(authorized),
    ):
        try:
            return quote(
                payload["purchase_minor"],
                payload["sale_minor"],
                payload.get("costs", {}),
                FlipPolicy(),
                confidence=payload.get(
                    "confidence", "LOW"
                ),
                condition=payload.get(
                    "condition", "unknown"
                ),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(
                422,
                str(exc),
            ) from exc

    return app
