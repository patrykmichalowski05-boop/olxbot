"""Deal-listing workspace ownership.

Revision ID: 0003_deal_workspace_fk
Revises: 0002_deal_timestamps
"""

from alembic import op

revision = "0003_deal_workspace_fk"
down_revision = "0002_deal_timestamps"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_listings_ws_id",
        "listings",
        ["workspace_id", "id"],
    )

    op.create_foreign_key(
        "fk_deals_workspace_listing",
        "deals",
        "listings",
        ["workspace_id", "listing_id"],
        ["workspace_id", "id"],
    )


def downgrade():
    op.drop_constraint(
        "fk_deals_workspace_listing",
        "deals",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_listings_ws_id",
        "listings",
        type_="unique",
    )
