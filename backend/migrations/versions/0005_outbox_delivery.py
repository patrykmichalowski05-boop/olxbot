"""Leased outbox and notification inbox.

Revision ID: 0005_outbox_delivery
Revises: 0004_outbox_audit
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_outbox_delivery"
down_revision = "0004_outbox_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "outbox_events",
        sa.Column(
            "status",
            sa.String(12),
            nullable=False,
            server_default="PENDING",
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "lease_until",
            sa.DateTime(timezone=True),
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "lease_token",
            sa.String(36),
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "last_error",
            sa.String(120),
        ),
    )

    op.execute(
        "UPDATE outbox_events "
        "SET status='DELIVERED' "
        "WHERE delivered=1"
    )

    op.create_check_constraint(
        "outbox_status_valid",
        "outbox_events",
        "status IN ('PENDING','CLAIMED','DELIVERED','DEAD')",
    )

    op.create_check_constraint(
        "outbox_attempts_nonnegative",
        "outbox_events",
        "attempts >= 0",
    )

    op.create_index(
        "ix_outbox_status_available",
        "outbox_events",
        ["status", "available_at"],
    )

    op.create_table(
        "notification_inbox",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            sa.String(36),
            sa.ForeignKey("outbox_events.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "event_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_notification_inbox_workspace_id",
        "notification_inbox",
        ["workspace_id"],
    )

    op.create_index(
        "ix_inbox_ws_created_id",
        "notification_inbox",
        ["workspace_id", "created_at", "id"],
    )


def downgrade():
    op.drop_index(
        "ix_inbox_ws_created_id",
        table_name="notification_inbox",
    )

    op.drop_index(
        "ix_notification_inbox_workspace_id",
        table_name="notification_inbox",
    )

    op.drop_table("notification_inbox")

    op.drop_index(
        "ix_outbox_status_available",
        table_name="outbox_events",
    )

    op.drop_constraint(
        "outbox_attempts_nonnegative",
        "outbox_events",
        type_="check",
    )

    op.drop_constraint(
        "outbox_status_valid",
        "outbox_events",
        type_="check",
    )

    for field in (
        "last_error",
        "lease_token",
        "lease_until",
        "available_at",
        "attempts",
        "status",
    ):
        op.drop_column(
            "outbox_events",
            field,
        )
