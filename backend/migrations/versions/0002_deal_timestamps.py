"""Deal and cost chronology.

Revision ID: 0002_deal_timestamps
Revises: 0001_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_deal_timestamps"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deals", sa.Column(
        "created_at", sa.DateTime(timezone=True),
        nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
    ))
    op.add_column("deal_costs", sa.Column(
        "created_at", sa.DateTime(timezone=True),
        nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"),
    ))
    op.create_index("ix_deals_workspace_created_id", "deals",
                    ["workspace_id", "created_at", "id"])


def downgrade():
    op.drop_index("ix_deals_workspace_created_id", table_name="deals")
    op.drop_column("deal_costs", "created_at")
    op.drop_column("deals", "created_at")
