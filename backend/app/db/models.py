"""SQLAlchemy 2. Schema managed by Alembic."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    func,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    username: Mapped[str] = mapped_column(
        String(80), unique=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255)
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(120)
    )


class Membership(Base):
    __tablename__ = "memberships"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(12)
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','admin','member')",
            name="role_valid",
        ),
    )


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    source_scope: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    external_id: Mapped[str] = mapped_column(
        String(240), nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "id",
            name="uq_listings_ws_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "source",
            "source_scope",
            "external_id",
            name="uq_listing_scope",
        ),
    )


class ListingObservation(Base):
    __tablename__ = "listing_observations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.id"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    price_minor: Mapped[int | None] = mapped_column(
        Integer
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "revision",
            name="uq_listing_revision",
        ),
        CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="observation_price_nonnegative",
        ),
        Index(
            "ix_observation_listing_revision",
            "listing_id",
            "revision",
        ),
    )


class ValuationRun(Base):
    __tablename__ = "valuation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("listing_observations.id"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    result: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(12), nullable=False
    )
    purchase_minor: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    sale_minor: Mapped[int | None] = mapped_column(
        Integer
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "listing_id"],
            ["listings.workspace_id", "listings.id"],
            name="fk_deals_workspace_listing",
        ),
        Index("ix_deals_workspace_created_id", "workspace_id", "created_at", "id"),
        UniqueConstraint(
            "workspace_id",
            "listing_id",
            name="uq_deal_workspace_listing",
        ),
        CheckConstraint(
            "purchase_minor > 0",
            name="purchase_positive",
        ),
        CheckConstraint(
            "sale_minor IS NULL OR sale_minor > 0",
            name="sale_positive",
        ),
        CheckConstraint(
            "status IN ('BOUGHT','SOLD')",
            name="deal_status_valid",
        ),
    )


class DealCost(Base):
    __tablename__ = "deal_costs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deal_id: Mapped[str] = mapped_column(
        ForeignKey("deals.id"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "amount_minor >= 0",
            name="cost_nonnegative",
        ),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        primary_key=True,
    )
    request_key: Mapped[str] = mapped_column(
        String(128), primary_key=True
    )
    operation: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    response: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )
    delivered: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    __table_args__ = (
        CheckConstraint(
            "delivered IN (0,1)",
            name="outbox_delivered_bool",
        ),
    )
