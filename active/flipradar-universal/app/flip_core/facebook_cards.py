"""Read-only import of Facebook Marketplace card observations."""

from collections import Counter
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
import re
import sqlite3

from .category_router import categorize
from .contracts import RawListing, SourceStatus


ALLOWED_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
}

REQUIRED = {
    "listing_id",
    "url",
    "title",
    "price",
}


def canonical_facebook_url(url, listing_id):
    try:
        parsed = urlsplit(str(url or "").strip())

        if parsed.scheme not in ("https", "http"):
            return None

        if parsed.hostname not in ALLOWED_HOSTS:
            return None

        if parsed.username or parsed.password:
            return None

        match = re.fullmatch(
            r"/marketplace/item/(\d+)/?",
            parsed.path,
            flags=re.I,
        )

        if not match:
            return None

        extracted = match.group(1)

        if extracted != str(listing_id):
            return None

        return (
            "https://www.facebook.com/"
            f"marketplace/item/{extracted}"
        )

    except ValueError:
        return None


def raw_card_price(value):
    """Validate numeric data without assuming its currency."""

    if isinstance(value, bool) or value is None:
        return None

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

    if not amount.is_finite():
        return None

    if not Decimal("0") < amount <= Decimal("10000000"):
        return None

    if amount.as_tuple().exponent < -2:
        return None

    return str(amount)


def convert_card(row):
    data = dict(row)

    listing_id = str(
        data.get("listing_id") or ""
    ).strip()

    if not listing_id.isascii() or not listing_id.isdigit():
        return None, "INVALID_ID"

    canonical = canonical_facebook_url(
        data.get("url"),
        listing_id,
    )

    if not canonical:
        return None, "INVALID_URL"

    title = str(
        data.get("title") or ""
    ).strip()[:300]

    if not title:
        return None, "MISSING_TITLE"

    price = raw_card_price(
        data.get("price")
    )

    listing = RawListing(
        platform="FACEBOOK",
        external_id=listing_id,
        canonical_url=canonical,
        title=title,
        description="",
        price_minor=None,
        currency="UNKNOWN",
        status=SourceStatus.UNKNOWN,
        fetched_at=str(
            data.get("last_seen") or ""
        ),
        parser_version="facebook-card-v1",
    )

    category = categorize(listing)

    payload = {
        "platform": "FACEBOOK",
        "external_id": listing_id,
        "canonical_url": canonical,
        "title": title,
        "description": "",
        "price_minor": None,
        "currency": "UNKNOWN",
        "status": "UNKNOWN",
        "attributes": {},
        "classification": category.category,
        "source_evidence": {
            "type": "FACEBOOK_CARD_ONLY",
            "card_price_unverified": price,
            "currency_verified": False,
            "specifications_verified": False,
            "availability_verified": False,
            "last_seen": str(
                data.get("last_seen") or ""
            ),
        },
    }

    return payload, None


def read_cards(db_path, limit=5000):
    db_path = Path(db_path).resolve()

    if not db_path.is_file():
        raise FileNotFoundError(
            f"Brak bazy Facebooka: {db_path}"
        )

    if not 1 <= limit <= 50000:
        raise ValueError("Nieprawidlowy limit")

    uri = db_path.as_uri() + "?mode=ro"

    with closing(sqlite3.connect(
        uri,
        uri=True,
        timeout=20,
    )) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")

        existing = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='facebook_offers'
        """).fetchone()

        if existing is None:
            raise ValueError(
                "Brak tabeli facebook_offers"
            )

        columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(facebook_offers)"
            )
        }

        missing = REQUIRED - columns

        if missing:
            raise ValueError(
                "Brak kolumn Facebook: "
                + ", ".join(sorted(missing))
            )

        order_by = (
            "last_seen DESC"
            if "last_seen" in columns
            else "listing_id DESC"
        )

        rows = db.execute(
            "SELECT * FROM facebook_offers "
            f"ORDER BY {order_by} LIMIT ?",
            (limit,),
        ).fetchall()

    accepted = []
    rejected = Counter()
    categories = Counter()

    analyzed = 0
    alerts = 0
    prices = 0

    for row in rows:
        data = dict(row)

        analyzed += int(
            data.get("analyzed") == 1
        )

        alerts += int(
            data.get("alert_sent") == 1
        )

        payload, reason = convert_card(data)

        if reason:
            rejected[reason] += 1
            continue

        if payload["source_evidence"][
            "card_price_unverified"
        ] is not None:
            prices += 1

        categories[
            payload["classification"]
        ] += 1

        accepted.append(payload)

    report = {
        "database_found": True,
        "cards_inspected": len(rows),
        "cards_importable": len(accepted),
        "cards_rejected": dict(rejected),
        "cards_with_unverified_price": prices,
        "analyzed_cards": analyzed,
        "alerts_sent_records": alerts,
        "categories_from_titles": dict(categories),
        "currency_verified": 0,
        "detailed_specs_verified": 0,
        "confirmed_active_listings": 0,
        "automatic_valuation_allowed": False,
        "production_writes": False,
    }

    return accepted, report
