"""Transaction ledger. No external IO in DB transactions."""

import hashlib
import json
import uuid

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Listing,
    Deal,
    DealCost,
    IdempotencyRecord,
    OutboxEvent,
)


class DealConflict(ValueError):
    pass


def _amount(value, *, positive=False):
    if (
        type(value) is not int
        or value < 0
        or value > 1_000_000_000
        or (positive and value == 0)
    ):
        raise ValueError("Invalid amount_minor")


def _apply(
    session: Session,
    workspace_id: str,
    key: str,
    kind: str,
    payload: dict,
    fn,
):
    if (
        not isinstance(workspace_id, str)
        or not workspace_id
    ):
        raise ValueError("Workspace required")

    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise ValueError(
            "Idempotency-Key must have 8-128 chars"
        )

    fingerprint = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
        ).encode()
    ).hexdigest()

    try:
        with session.begin():
            row = session.get(
                IdempotencyRecord,
                (workspace_id, key),
            )

            if row:
                if (
                    row.operation != kind
                    or row.fingerprint != fingerprint
                ):
                    raise DealConflict(
                        "Idempotency key reused"
                    )
                return row.response

            result = fn()

            session.add(
                IdempotencyRecord(
                    workspace_id=workspace_id,
                    request_key=key,
                    operation=kind,
                    fingerprint=fingerprint,
                    response=result,
                )
            )

            session.flush()
            return result

    except IntegrityError as exc:
        # Concurrent unique-key conflicts: reread after rollback.
        with session.begin():
            row = session.get(
                IdempotencyRecord,
                (workspace_id, key),
            )

            if row:
                if (
                    row.operation != kind
                    or row.fingerprint != fingerprint
                ):
                    raise DealConflict(
                        "Idempotency key reused"
                    ) from exc

                return row.response

        raise DealConflict(
            "Concurrent conflict"
        ) from exc


def purchase(
    session: Session,
    workspace_id: str,
    listing_id: str,
    amount_minor: int,
    key: str,
):
    _amount(amount_minor, positive=True)

    def work():
        listing = session.get(Listing, listing_id)

        if (
            listing is None
            or listing.workspace_id != workspace_id
        ):
            raise DealConflict(
                "Listing not found in workspace"
            )

        exists = session.scalar(
            select(Deal.id).where(
                Deal.workspace_id == workspace_id,
                Deal.listing_id == listing_id,
            )
        )

        if exists:
            raise DealConflict(
                "Listing already purchased"
            )

        deal_id = str(uuid.uuid4())

        session.add(
            Deal(
                id=deal_id,
                workspace_id=workspace_id,
                listing_id=listing_id,
                status="BOUGHT",
                purchase_minor=amount_minor,
                sale_minor=None,
                currency="PLN",
            )
        )

        session.add(
            OutboxEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                event_type="DEAL_PURCHASED",
                payload={"deal_id": deal_id},
            )
        )

        return {
            "deal_id": deal_id,
            "status": "BOUGHT",
        }

    return _apply(
        session,
        workspace_id,
        key,
        "purchase",
        {
            "listing_id": listing_id,
            "amount": amount_minor,
        },
        work,
    )


def add_cost(
    session: Session,
    workspace_id: str,
    deal_id: str,
    kind: str,
    amount_minor: int,
    key: str,
):
    _amount(amount_minor)

    if (
        not isinstance(kind, str)
        or not 1 <= len(kind) <= 32
    ):
        raise ValueError("Invalid cost kind")

    def work():
        deal = session.get(Deal, deal_id)

        if (
            deal is None
            or deal.workspace_id != workspace_id
        ):
            raise DealConflict(
                "Deal not found in workspace"
            )

        cost_id = str(uuid.uuid4())

        session.add(
            DealCost(
                id=cost_id,
                deal_id=deal_id,
                kind=kind,
                amount_minor=amount_minor,
            )
        )

        session.add(
            OutboxEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                event_type="DEAL_COST_ADDED",
                payload={
                    "deal_id": deal_id,
                    "cost_id": cost_id,
                    "kind": kind,
                    "amount_minor": amount_minor,
                },
            )
        )

        return {
            "cost_id": cost_id,
            "deal_id": deal_id,
        }

    return _apply(
        session,
        workspace_id,
        key,
        "cost",
        {
            "deal_id": deal_id,
            "kind": kind,
            "amount": amount_minor,
        },
        work,
    )


def sell(
    session: Session,
    workspace_id: str,
    deal_id: str,
    amount_minor: int,
    key: str,
):
    _amount(amount_minor, positive=True)

    def work():
        deal = session.scalar(
            select(Deal)
            .where(
                Deal.id == deal_id,
                Deal.workspace_id == workspace_id,
            )
            .with_for_update()
        )

        if (
            deal is None
            or deal.workspace_id != workspace_id
            or deal.status != "BOUGHT"
        ):
            raise DealConflict(
                "Deal not found or already sold"
            )

        deal.sale_minor = amount_minor
        deal.status = "SOLD"

        session.add(
            OutboxEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                event_type="DEAL_SOLD",
                payload={"deal_id": deal_id},
            )
        )

        return {
            "deal_id": deal_id,
            "status": "SOLD",
        }

    return _apply(
        session,
        workspace_id,
        key,
        "sale",
        {
            "deal_id": deal_id,
            "amount": amount_minor,
        },
        work,
    )


def summary(
    session: Session,
    workspace_id: str,
    deal_id: str,
):
    deal = session.get(Deal, deal_id)

    if (
        deal is None
        or deal.workspace_id != workspace_id
    ):
        return None

    costs = session.scalar(
        select(
            func.coalesce(
                func.sum(DealCost.amount_minor),
                0,
            )
        ).where(
            DealCost.deal_id == deal_id
        )
    )

    return {
        "deal_id": deal_id,
        "status": deal.status,
        "purchase_minor": deal.purchase_minor,
        "sale_minor": deal.sale_minor,
        "cost_minor": costs,
        "realized_profit_minor": (
            deal.sale_minor
            - deal.purchase_minor
            - costs
            if deal.status == "SOLD"
            else None
        ),
    }
