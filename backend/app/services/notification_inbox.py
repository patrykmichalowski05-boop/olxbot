"""Workspace-scoped internal notification inbox."""

from sqlalchemy import select, and_, or_

from backend.app.db.models import NotificationInbox


def page(
    session,
    workspace_id,
    *,
    limit=20,
    before_id=None,
):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError(
            "Invalid notification limit"
        )

    query = select(NotificationInbox).where(
        NotificationInbox.workspace_id == workspace_id
    )

    if before_id:
        pivot = session.scalar(
            select(NotificationInbox).where(
                NotificationInbox.id == before_id,
                NotificationInbox.workspace_id == workspace_id,
            )
        )

        if pivot is None:
            raise ValueError(
                "Invalid notification cursor"
            )

        query = query.where(
            or_(
                NotificationInbox.created_at
                < pivot.created_at,
                and_(
                    NotificationInbox.created_at
                    == pivot.created_at,
                    NotificationInbox.id
                    < pivot.id,
                ),
            )
        )

    rows = session.scalars(
        query.order_by(
            NotificationInbox.created_at.desc(),
            NotificationInbox.id.desc(),
        ).limit(limit + 1)
    ).all()

    more = len(rows) > limit
    items = rows[:limit]

    return {
        "items": [
            {
                "id": row.id,
                "event_type": row.event_type,
                "payload": row.payload,
                "created_at": row.created_at.isoformat(),
            }
            for row in items
        ],
        "next_before_id": (
            items[-1].id
            if more
            else None
        ),
    }
