"""Isolated PostgreSQL endpoints attached to existing API."""

from pathlib import Path

from fastapi import (
    Depends,
    Header,
    HTTPException,
    Query,
)
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from universal_v2.mobile_bridge import (
    create_app as create_mobile_app,
)
from universal_v2.bridge_config import BridgeConfig

from backend.app.core.settings import Settings
from backend.app.db.session import make_session_factory
from backend.app.api.security import WorkspaceSecurity
from backend.app.services.listing_ingest import ingest
from backend.app.services.notification_inbox import page as inbox_page
from backend.app.services.deals import (
    DealConflict,
    purchase,
    add_cost,
    sell,
    summary,
    cost_items,
    deal_page,
    deal_events,
)


class IngestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=2, max_length=40)
    source_scope: str = Field(min_length=1, max_length=80)
    external_id: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=500)
    price_minor: StrictInt | None = Field(
        default=None,
        ge=0,
        le=1_000_000_000,
    )
    payload: dict = Field(default_factory=dict)


class PurchaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1, max_length=36)
    amount_minor: StrictInt = Field(gt=0, le=1_000_000_000)


class CostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=32)
    amount_minor: StrictInt = Field(ge=0, le=1_000_000_000)


class SaleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_minor: StrictInt = Field(gt=0, le=1_000_000_000)


def create_app():
    settings = Settings()
    bridge = BridgeConfig.from_env()

    # Compose legacy/mobile/universal endpoints.
    app = create_mobile_app()

    security = WorkspaceSecurity(bridge.auth_db)

    engine, session_factory = make_session_factory(
        settings.database_url
    )

    app.state.backend_engine = engine

    def db_session():
        with session_factory() as db:
            yield db

    def current_user(
        authorization: str | None = Header(default=None)
    ):
        return security.current_user(authorization)

    def reader(
        workspace_id: str,
        user_id: str = Depends(current_user),
    ):
        with session_factory() as db:
            security.require_role(
                db,
                workspace_id,
                user_id,
                write=False,
            )

        return user_id

    def writer(
        workspace_id: str,
        user_id: str = Depends(current_user),
    ):
        # Separate session: do not start transaction
        # on the service's write session.
        with session_factory() as db:
            security.require_role(
                db,
                workspace_id,
                user_id,
                write=True,
            )

        return user_id

    def execute(callback):
        try:
            return callback()

        except DealConflict as exc:
            raise HTTPException(
                409,
                str(exc),
            ) from None

        except ValueError as exc:
            raise HTTPException(
                422,
                str(exc),
            ) from None

    @app.post("/api/v2/workspaces/{workspace_id}/deals")
    def create_deal(
        workspace_id: str,
        body: PurchaseBody,
        key: str = Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
        ),
        _: str = Depends(writer),
        db: Session = Depends(db_session),
    ):
        return execute(
            lambda: purchase(
                db,
                workspace_id,
                body.listing_id,
                body.amount_minor,
                key,
                actor_id=_,
            )
        )

    @app.post(
        "/api/v2/workspaces/{workspace_id}"
        "/deals/{deal_id}/costs"
    )
    def create_cost(
        workspace_id: str,
        deal_id: str,
        body: CostBody,
        key: str = Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
        ),
        _: str = Depends(writer),
        db: Session = Depends(db_session),
    ):
        return execute(
            lambda: add_cost(
                db,
                workspace_id,
                deal_id,
                body.kind,
                body.amount_minor,
                key,
                actor_id=_,
            )
        )

    @app.post(
        "/api/v2/workspaces/{workspace_id}"
        "/deals/{deal_id}/sell"
    )
    def sell_deal(
        workspace_id: str,
        deal_id: str,
        body: SaleBody,
        key: str = Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
        ),
        _: str = Depends(writer),
        db: Session = Depends(db_session),
    ):
        return execute(
            lambda: sell(
                db,
                workspace_id,
                deal_id,
                body.amount_minor,
                key,
                actor_id=_,
            )
        )

    @app.get(
        "/api/v2/workspaces/{workspace_id}"
        "/deals/{deal_id}"
    )
    def read_deal(
        workspace_id: str,
        deal_id: str,
        _: str = Depends(reader),
        db: Session = Depends(db_session),
    ):
        result = summary(db, workspace_id, deal_id)

        if result is None:
            raise HTTPException(
                404,
                "Deal not found",
            )

        return result

    @app.get(
        "/api/v2/workspaces/{workspace_id}/deals/{deal_id}/costs"
    )
    def read_costs(
        workspace_id: str,
        deal_id: str,
        _: str = Depends(reader),
        db: Session = Depends(db_session),
    ):
        result = cost_items(db, workspace_id, deal_id)
        if result is None:
            raise HTTPException(404, "Deal not found")
        return result

    @app.get("/api/v2/workspaces/{workspace_id}/deals")
    def list_deals(
        workspace_id: str,
        status: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        before_id: str | None = Query(default=None, max_length=36),
        _: str = Depends(reader),
        db: Session = Depends(db_session),
    ):
        return execute(lambda: deal_page(
            db, workspace_id, status=status,
            limit=limit, before_id=before_id,
        ))

    @app.get(
        "/api/v2/workspaces/{workspace_id}/deals/{deal_id}/events"
    )
    def read_deal_events(
        workspace_id: str,
        deal_id: str,
        _: str = Depends(reader),
        db: Session = Depends(db_session),
    ):
        result = deal_events(db, workspace_id, deal_id)

        if result is None:
            raise HTTPException(
                404,
                "Deal not found",
            )

        return result

    @app.get(
        "/api/v2/healthz",
        include_in_schema=False,
    )
    def healthz():
        try:
            with session_factory() as db:
                db.execute(text("SELECT 1"))

        except SQLAlchemyError:
            raise HTTPException(
                503,
                "Backend unavailable",
            ) from None

        return {"status": "ok"}

    @app.get(
        "/api/v2/workspaces/{workspace_id}/notifications"
    )
    def list_notifications(
        workspace_id: str,
        limit: int = Query(
            default=20, ge=1, le=100
        ),
        before_id: str | None = Query(
            default=None, max_length=36
        ),
        _: str = Depends(reader),
        db: Session = Depends(db_session),
    ):
        return execute(
            lambda: inbox_page(
                db,
                workspace_id,
                limit=limit,
                before_id=before_id,
            )
        )

    @app.post(
        "/api/v2/workspaces/{workspace_id}/listings/ingest"
    )
    def ingest_listing(
        workspace_id: str,
        body: IngestBody,
        key: str = Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
        ),
        user_id: str = Depends(writer),
        db: Session = Depends(db_session),
    ):
        return execute(lambda: ingest(
            db,
            workspace_id,
            source=body.source,
            source_scope=body.source_scope,
            external_id=body.external_id,
            title=body.title,
            price_minor=body.price_minor,
            payload=body.payload,
            key=key,
        ))

    return app
