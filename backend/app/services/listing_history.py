"""History of listing observations with workspace isolation."""

from sqlalchemy import select
from backend.app.db.models import Listing, ListingObservation


def history(
    session,
    workspace_id,
    listing_id,
    *,
    limit=30,
    before_revision=None,
):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Invalid limit')

    if before_revision is not None and (
        type(before_revision) is not int
        or before_revision < 1
    ):
        raise ValueError('Invalid cursor')

    listing = session.scalar(
        select(Listing).where(
            Listing.workspace_id == workspace_id,
            Listing.id == listing_id,
        )
    )

    if listing is None:
        return None

    query = select(ListingObservation).where(
        ListingObservation.listing_id == listing.id
    )

    if before_revision is not None:
        query = query.where(
            ListingObservation.revision < before_revision
        )

    rows = session.scalars(
        query.order_by(
            ListingObservation.revision.desc()
        ).limit(limit + 1)
    ).all()

    visible = rows[:limit]

    return {
        'listing_id': listing.id,
        'title': listing.title,
        'items': [
            {
                'revision': row.revision,
                'price_minor': row.price_minor,
                'currency': row.currency,
            }
            for row in visible
        ],
        'next_before_revision': (
            visible[-1].revision
            if len(rows) > limit
            else None
        ),
    }
