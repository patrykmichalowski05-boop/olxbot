"""Initial isolated schema.

Revision ID: 0001_foundation
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
    )

    op.create_table(
        "memberships",
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.String(36),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(12), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner','admin','member')",
            name="role_valid",
        ),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("source_scope", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(240), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "source", "source_scope",
            "external_id",
            name="uq_listing_scope",
        ),
    )

    op.create_index(
        "ix_listings_workspace_id",
        "listings",
        ["workspace_id"],
    )

    op.create_table(
        "listing_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_id", sa.String(36),
            sa.ForeignKey("listings.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("price_minor", sa.Integer),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.UniqueConstraint(
            "listing_id", "revision",
            name="uq_listing_revision",
        ),
        sa.CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="observation_price_nonnegative",
        ),
    )

    op.create_index(
        "ix_observation_listing_revision",
        "listing_observations",
        ["listing_id", "revision"],
    )

    op.create_table(
        "valuation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "observation_id", sa.String(36),
            sa.ForeignKey("listing_observations.id"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
    )

    op.create_index(
        "ix_valuation_runs_workspace_id",
        "valuation_runs",
        ["workspace_id"],
    )

    op.create_table(
        "deals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "listing_id", sa.String(36),
            sa.ForeignKey("listings.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("purchase_minor", sa.Integer, nullable=False),
        sa.Column("sale_minor", sa.Integer),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "listing_id",
            name="uq_deal_workspace_listing",
        ),
        sa.CheckConstraint(
            "purchase_minor > 0",
            name="purchase_positive",
        ),
        sa.CheckConstraint(
            "sale_minor IS NULL OR sale_minor > 0",
            name="sale_positive",
        ),
        sa.CheckConstraint(
            "status IN ('BOUGHT','SOLD')",
            name="deal_status_valid",
        ),
    )

    op.create_index(
        "ix_deals_workspace_id",
        "deals",
        ["workspace_id"],
    )

    op.create_table(
        "deal_costs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "deal_id", sa.String(36),
            sa.ForeignKey("deals.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "amount_minor >= 0",
            name="cost_nonnegative",
        ),
    )

    op.create_index(
        "ix_deal_costs_deal_id",
        "deal_costs",
        ["deal_id"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            primary_key=True,
        ),
        sa.Column(
            "request_key", sa.String(128),
            primary_key=True,
        ),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("response", sa.JSON, nullable=False),
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(36),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "delivered", sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.CheckConstraint(
            "delivered IN (0,1)",
            name="outbox_delivered_bool",
        ),
    )

    op.create_index(
        "ix_outbox_events_workspace_id",
        "outbox_events",
        ["workspace_id"],
    )


def downgrade():
    for name in (
        "outbox_events",
        "idempotency_records",
        "deal_costs",
        "deals",
        "valuation_runs",
        "listing_observations",
        "listings",
        "memberships",
        "workspaces",
        "users",
    ):
        op.drop_table(name)
