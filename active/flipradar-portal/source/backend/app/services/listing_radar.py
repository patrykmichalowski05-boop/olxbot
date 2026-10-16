"""Workspace-scoped PostgreSQL radar."""

from sqlalchemy import (
    select,
    and_,
    or_,
)

from backend.app.db.models import (
    Listing,
    ListingObservation,
)


def page(
    session,
    workspace_id,
    *,
    limit=20,
    before_id=None,
    q="",
):
    if (
        type(limit) is not int
        or not 1 <= limit <= 50
    ):
        raise ValueError("Invalid limit")

    if (
        not isinstance(q, str)
        or len(q) > 120
    ):
        raise ValueError("Invalid search")

    query = select(Listing).where(
        Listing.workspace_id == workspace_id
    )

    if q.strip():
        escaped = (
            q.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        query = query.where(
            Listing.title.ilike(
                "%" + escaped + "%",
                escape="\\",
            )
        )

    if before_id is not None:
        pivot = session.scalar(
            select(Listing).where(
                Listing.id == before_id,
                Listing.workspace_id == workspace_id,
            )
        )

        if pivot is None:
            raise ValueError("Invalid cursor")

        query = query.where(
            or_(
                Listing.created_at < pivot.created_at,
                and_(
                    Listing.created_at
                    == pivot.created_at,
                    Listing.id < pivot.id,
                ),
            )
        )

    rows = session.scalars(
        query.order_by(
            Listing.created_at.desc(),
            Listing.id.desc(),
        ).limit(limit + 1)
    ).all()

    visible = rows[:limit]
    items = []

    for row in visible:
        last = session.scalar(
            select(ListingObservation)
            .where(
                ListingObservation.listing_id
                == row.id
            )
            .order_by(
                ListingObservation.revision.desc()
            )
            .limit(1)
        )

        items.append({
            "id": row.id,
            "source": row.source,
            "source_scope": row.source_scope,
            "external_id": row.external_id,
            "title": row.title,
            "created_at": row.created_at.isoformat(),
            "price_minor": (
                last.price_minor
                if last
                else None
            ),
            "currency": (
                last.currency
                if last
                else None
            ),
            "revision": (
                last.revision
                if last
                else None
            ),
        })

    return {
        "items": items,
        "next_before_id": (
            visible[-1].id
            if len(rows) > limit
            else None
        ),
    }
