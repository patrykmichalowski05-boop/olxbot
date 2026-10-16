"""Adapter historycznych snapshotow OLX i Facebooka."""

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

from .contracts import RawListing, SourceStatus
from .listing_repository import parse_json, platform_from
from .money import to_minor


class SnapshotBridgeError(ValueError):
    pass


def normalize_snapshot(record):
    row = dict(record)

    url = str(row.get("url") or "").strip()
    parsed = urlsplit(url)

    if parsed.scheme not in ("http", "https"):
        raise SnapshotBridgeError("INVALID_URL")

    host = (parsed.hostname or "").lower()

    platform = platform_from(url)

    if platform not in ("OLX", "FACEBOOK"):
        raise SnapshotBridgeError("UNKNOWN_PLATFORM")

    details = parse_json(row.get("details_json"))
    valuation = parse_json(row.get("valuation_json"))
    action = parse_json(row.get("action_json"))

    currency = str(
        details.get("currency") or "PLN"
    ).strip().upper()

    if currency != "PLN":
        raise SnapshotBridgeError("UNSUPPORTED_CURRENCY")

    canonical_url = urlunsplit((
        "https",
        host,
        parsed.path.rstrip("/") or "/",
        "",
        "",
    ))

    if platform == "OLX":
        match = re.search(
            r"\bID[A-Za-z0-9]+\b",
            parsed.path,
            re.IGNORECASE,
        )
        external_id = (
            match.group(0).upper()
            if match else None
        )
    else:
        match = re.search(
            r"/marketplace/item/(\d+)",
            parsed.path,
        )
        external_id = (
            match.group(1) if match else None
        )

    if not external_id:
        external_id = hashlib.sha256(
            canonical_url.encode("utf-8")
        ).hexdigest()[:32]

    title = str(
        row.get("title")
        or details.get("title")
        or ""
    ).strip()

    if not title:
        raise SnapshotBridgeError("MISSING_TITLE")

    price = row.get("price")

    if price is None:
        price_minor = None
    else:
        try:
            price_minor = to_minor(
                price, positive=True
            )
        except ValueError:
            raise SnapshotBridgeError(
                "INVALID_PRICE"
            ) from None

    if (
        details.get("is_sold") is True
        or details.get("is_live") is False
    ):
        status = SourceStatus.REMOVED
    elif (
        details.get("is_live") is True
        and details.get("is_sold") is False
    ):
        status = SourceStatus.ACTIVE
    else:
        status = SourceStatus.UNKNOWN

    description = str(
        details.get("description") or ""
    )[:12000]

    listing = RawListing(
        platform=platform,
        external_id=external_id,
        canonical_url=canonical_url,
        title=title,
        description=description,
        price_minor=price_minor,
        currency=currency,
        status=status,
        fetched_at=str(
            row.get("created_at") or ""
        ),
        parser_version="legacy-snapshot-v1",
    )

    attributes = {
        key: details.get(key)
        for key in (
            "cpu",
            "gpu",
            "ram",
            "disks",
            "motherboard",
            "psu",
        )
    }

    payload = {
        "platform": listing.platform,
        "external_id": listing.external_id,
        "canonical_url": listing.canonical_url,
        "title": listing.title,
        "description": listing.description,
        "price_minor": listing.price_minor,
        "currency": listing.currency,
        "status": listing.status.value,
        "attributes": attributes,
    }

    analysis = {
        "legacy_valuation": valuation,
        "legacy_action": action,
        "legacy_score": row.get("score"),
        "legacy_mode": row.get("mode"),
        "legacy_trigger": row.get("trigger"),
    }

    return listing, payload, analysis
