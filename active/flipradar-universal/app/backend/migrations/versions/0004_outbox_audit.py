"""Outbox actor and creation time.

Revision ID: 0004_outbox_audit
Revises: 0003_deal_workspace_fk
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_outbox_audit"
down_revision = "0003_deal_workspace_fk"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "outbox_events",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "actor_user_id",
            sa.String(36),
        ),
    )

    op.create_foreign_key(
        "fk_outbox_actor_user",
        "outbox_events",
        "users",
        ["actor_user_id"],
        ["id"],
    )

    op.create_index(
        "ix_outbox_ws_created_id",
        "outbox_events",
        ["workspace_id", "created_at", "id"],
    )


def downgrade():
    op.drop_index(
        "ix_outbox_ws_created_id",
        table_name="outbox_events",
    )

    op.drop_constraint(
        "fk_outbox_actor_user",
        "outbox_events",
        type_="foreignkey",
    )

    op.drop_column(
        "outbox_events",
        "actor_user_id",
    )

    op.drop_column(
        "outbox_events",
        "created_at",
    )
