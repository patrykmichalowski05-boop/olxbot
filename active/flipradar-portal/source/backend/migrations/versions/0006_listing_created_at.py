"""Listing chronology.

Revision ID: 0006_listing_created_at
Revises: 0005_outbox_delivery
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_listing_created_at"
down_revision = "0005_outbox_delivery"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "listings",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
        ),
    )

    op.create_index(
        "ix_listings_ws_created_id",
        "listings",
        [
            "workspace_id",
            "created_at",
            "id",
        ],
    )


def downgrade():
    op.drop_index(
        "ix_listings_ws_created_id",
        table_name="listings",
    )

    op.drop_column(
        "listings",
        "created_at",
    )
