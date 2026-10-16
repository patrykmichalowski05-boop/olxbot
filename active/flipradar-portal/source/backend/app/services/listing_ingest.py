"""Idempotent manual offer ingestion."""

import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Workspace,
    Listing,
    ListingObservation,
    OutboxEvent,
)

from backend.app.services.deals import (
    DealConflict,
    _apply,
    _amount,
)


def ingest(
    session: Session,
    workspace_id: str,
    *,
    source: str,
    source_scope: str,
    external_id: str,
    title: str,
    price_minor: int | None,
    payload: dict,
    key: str,
):
    if (
        not isinstance(source, str)
        or not re.fullmatch(
            r"[A-Z][A-Z0-9_]{1,39}",
            source,
        )
    ):
        raise ValueError("Invalid source")

    for label, value, maxlen in (
        ("scope", source_scope, 80),
        ("external_id", external_id, 240),
        ("title", title, 500),
    ):
        if (
            not isinstance(value, str)
            or not 1 <= len(value.strip()) <= maxlen
        ):
            raise ValueError("Invalid " + label)

    if price_minor is not None:
        _amount(price_minor)

    if not isinstance(payload, dict):
        raise ValueError("Invalid payload")

    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Payload must be JSON"
        ) from exc

    if len(encoded.encode("utf-8")) > 8192:
        raise ValueError("Payload too large")

    source_scope = source_scope.strip()
    external_id = external_id.strip()
    title = title.strip()

    def work():
        owner = session.scalar(
            select(Workspace.id)
            .where(Workspace.id == workspace_id)
            .with_for_update()
        )

        if owner is None:
            raise DealConflict(
                "Workspace missing"
            )

        item = session.scalar(
            select(Listing).where(
                Listing.workspace_id == workspace_id,
                Listing.source == source,
                Listing.source_scope == source_scope,
                Listing.external_id == external_id,
            )
        )

        if item is None:
            item = Listing(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                source=source,
                source_scope=source_scope,
                external_id=external_id,
                title=title,
            )

            session.add(item)
            session.flush()

        else:
            item.title = title

        previous = session.scalar(
            select(ListingObservation)
            .where(
                ListingObservation.listing_id
                == item.id
            )
            .order_by(
                ListingObservation.revision.desc()
            )
            .limit(1)
        )

        if (
            previous is not None
            and previous.price_minor == price_minor
            and previous.payload == payload
        ):
            return {
                "listing_id": item.id,
                "observation_id": previous.id,
                "revision": previous.revision,
                "changed": False,
            }

        revision = (
            previous.revision + 1
            if previous
            else 1
        )

        observation = ListingObservation(
            id=str(uuid.uuid4()),
            listing_id=item.id,
            revision=revision,
            price_minor=price_minor,
            currency="PLN",
            payload=payload,
        )

        session.add(observation)

        if (
            previous is not None
            and previous.price_minor is not None
            and price_minor is not None
            and price_minor < previous.price_minor
        ):
            session.add(OutboxEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                event_type="LISTING_PRICE_DROP",
                payload={
                    "listing_id": item.id,
                    "from_minor": previous.price_minor,
                    "to_minor": price_minor,
                    "revision": revision,
                },
            ))

        return {
            "listing_id": item.id,
            "observation_id": observation.id,
            "revision": revision,
            "changed": True,
        }

    return _apply(
        session,
        workspace_id,
        key,
        "listing_ingest",
        {
            "source": source,
            "scope": source_scope,
            "external_id": external_id,
            "title": title,
            "price_minor": price_minor,
            "payload": payload,
        },
        work,
    )
