"""PostgreSQL outbox to internal notification inbox."""

from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.app.db.models import (
    OutboxEvent,
    NotificationInbox,
)

MAX_ATTEMPTS = 5

SUPPORTED = frozenset({
    "DEAL_PURCHASED",
    "DEAL_COST_ADDED",
    "DEAL_SOLD",
})


def claim(
    session: Session,
    *,
    limit=10,
    lease_seconds=90,
):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Invalid claim limit")

    if (
        type(lease_seconds) is not int
        or not 15 <= lease_seconds <= 3600
    ):
        raise ValueError("Invalid lease duration")

    now = datetime.now(timezone.utc)
    claimed = []

    with session.begin():
        events = session.scalars(
            select(OutboxEvent).where(
                or_(
                    and_(
                        OutboxEvent.status == "PENDING",
                        OutboxEvent.available_at <= now,
                    ),
                    and_(
                        OutboxEvent.status == "CLAIMED",
                        OutboxEvent.lease_until <= now,
                    ),
                )
            )
            .order_by(
                OutboxEvent.created_at,
                OutboxEvent.id,
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()

        for event in events:
            if event.attempts >= MAX_ATTEMPTS:
                event.status = "DEAD"
                event.lease_until = None
                event.lease_token = None
                event.last_error = "Retries exhausted"
                continue

            event.attempts += 1
            event.status = "CLAIMED"

            event.lease_until = (
                now + timedelta(seconds=lease_seconds)
            )

            event.lease_token = str(uuid.uuid4())

            claimed.append(
                (event.id, event.lease_token)
            )

    return claimed


def materialize(
    session: Session,
    event_id: str,
    lease_token: str,
):
    """
    Insert inbox notification and confirm outbox
    in one transaction.
    """

    with session.begin():
        event = session.scalar(
            select(OutboxEvent).where(
                OutboxEvent.id == event_id,
                OutboxEvent.lease_token == lease_token,
                OutboxEvent.status == "CLAIMED",
            ).with_for_update()
        )

        if event is None:
            return False

        if (
            event.lease_until is None
            or event.lease_until
            <= datetime.now(timezone.utc)
        ):
            return False

        if event.event_type not in SUPPORTED:
            raise ValueError(
                "Unsupported event type"
            )

        if (
            not isinstance(event.payload, dict)
            or not isinstance(
                event.payload.get("deal_id"),
                str,
            )
        ):
            raise ValueError(
                "Invalid event payload"
            )

        statement = insert(NotificationInbox).values(
            id=str(uuid.uuid4()),
            workspace_id=event.workspace_id,
            source_event_id=event.id,
            event_type=event.event_type,
            payload=event.payload,
        ).on_conflict_do_nothing(
            index_elements=["source_event_id"]
        )

        session.execute(statement)

        event.status = "DELIVERED"
        event.delivered = 1
        event.lease_until = None
        event.lease_token = None
        event.last_error = None

    return True


def backoff_seconds(attempts: int) -> int:
    if type(attempts) is not int or attempts < 1:
        raise ValueError(
            "Invalid attempt count"
        )

    return min(
        3600,
        10 * 2 ** min(attempts - 1, 9),
    )


def fail(
    session: Session,
    event_id: str,
    lease_token: str,
    *,
    reason="PROCESSING_FAILED",
):
    allowed = {
        "PROCESSING_FAILED",
        "INVALID_PAYLOAD",
        "UNSUPPORTED_EVENT",
    }

    if reason not in allowed:
        reason = "PROCESSING_FAILED"

    with session.begin():
        event = session.scalar(
            select(OutboxEvent).where(
                OutboxEvent.id == event_id,
                OutboxEvent.lease_token == lease_token,
                OutboxEvent.status == "CLAIMED",
            ).with_for_update()
        )

        if event is None:
            return False

        event.last_error = reason
        event.lease_until = None
        event.lease_token = None

        if (
            event.attempts >= MAX_ATTEMPTS
            or reason in (
                "INVALID_PAYLOAD",
                "UNSUPPORTED_EVENT",
            )
        ):
            event.status = "DEAD"

        else:
            event.status = "PENDING"

            event.available_at = (
                datetime.now(timezone.utc)
                + timedelta(
                    seconds=backoff_seconds(
                        event.attempts
                    )
                )
            )

    return True


def process_batch(factory, *, limit=10):
    with factory() as db:
        claimed = claim(db, limit=limit)

    counts = {
        "claimed": len(claimed),
        "delivered": 0,
        "failed": 0,
    }

    for event_id, token in claimed:
        try:
            with factory() as db:
                delivered = materialize(
                    db,
                    event_id,
                    token,
                )

            if delivered:
                counts["delivered"] += 1

        except Exception as exc:
            reason = (
                "INVALID_PAYLOAD"
                if isinstance(exc, ValueError)
                else "PROCESSING_FAILED"
            )

            with factory() as db:
                fail(
                    db,
                    event_id,
                    token,
                    reason=reason,
                )

            counts["failed"] += 1

    return counts
