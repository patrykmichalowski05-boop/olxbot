"""Read-only OLX and Facebook inventory. No live verification."""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .category_router import categorize
from .contracts import RawListing, SourceStatus


def freshness(value, now=None):
    """Observation age, NOT confirmation of availability."""
    if not value:
        return "UNKNOWN_TIME"

    try:
        dt = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            return "UNKNOWN_TIMEZONE"

        current = now or datetime.now(timezone.utc)
        age = current - dt.astimezone(timezone.utc)

        if age < -timedelta(minutes=5):
            return "FUTURE_TIMESTAMP"

        if age <= timedelta(days=7):
            return "RECENTLY_OBSERVED_UNVERIFIED"

        return "STALE_OBSERVATION"

    except (ValueError, TypeError, OverflowError):
        return "INVALID_TIME"


def load_latest(db_path, limit=10000):
    path = Path(db_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    if not 1 <= limit <= 50000:
        raise ValueError("Nieprawidlowy limit")

    with closing(sqlite3.connect(
        path.as_uri() + "?mode=ro",
        uri=True,
        timeout=20,
    )) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")

        rows = db.execute("""
            SELECT o.listing_key, o.payload_json
            FROM listing_observations o
            JOIN (
                SELECT listing_key, MAX(id) AS latest_id
                FROM listing_observations
                GROUP BY listing_key
            ) latest
              ON latest.listing_key = o.listing_key
             AND latest.latest_id = o.id
            ORDER BY o.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]


def convert(source, record):
    try:
        payload = json.loads(record["payload_json"])
        if not isinstance(payload, dict):
            raise ValueError("INVALID_JSON")

        platform = str(payload.get("platform") or "")
        external_id = str(payload.get("external_id") or "")

        if platform != source or not external_id:
            raise ValueError("SOURCE_MISMATCH")

        if record["listing_key"] != (
            platform + ":" + external_id
        ):
            raise ValueError("KEY_MISMATCH")

        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("MISSING_TITLE")

        currency = str(payload.get("currency") or "")
        price = payload.get("price_minor")

        if price is not None and (
            type(price) is not int or price <= 0
        ):
            raise ValueError("INVALID_PRICE")

        status_raw = payload.get("status", "UNKNOWN")

        status = (
            SourceStatus(status_raw)
            if status_raw in SourceStatus._value2member_map_
            else SourceStatus.UNKNOWN
        )

        listing = RawListing(
            platform=platform,
            external_id=external_id,
            canonical_url=str(
                payload.get("canonical_url") or ""
            ),
            title=title,
            description=str(
                payload.get("description") or ""
            ),
            price_minor=price,
            currency=currency,
            status=status,
            fetched_at="",
            parser_version="unified-shadow-v1",
        )

        category = categorize(
            listing,
            hints=payload.get("attributes"),
        )

        evidence = payload.get("source_evidence") or {}
        if not isinstance(evidence, dict):
            evidence = {}

        # OLX replay nie zachowal wiarygodnego
        # czasu obserwacji pierwotnej oferty.
        # NIE uzywamy daty importu shadow DB.
        source_time = (
            evidence.get("last_seen")
            if source == "FACEBOOK"
            else None
        )

        observed = freshness(source_time)

        flags = ["AVAILABILITY_UNVERIFIED"]

        if status == SourceStatus.REMOVED:
            flags.append("SOURCE_REPORTED_REMOVED")

        if source == "FACEBOOK":
            flags.extend((
                "CURRENCY_UNVERIFIED",
                "CARD_PRICE_UNVERIFIED",
                "SPECS_UNVERIFIED",
            ))
        else:
            flags.append("SOURCE_TIMESTAMP_NOT_RETAINED")

            if currency != "PLN":
                flags.append("CURRENCY_NOT_PLN")

            if price is None:
                flags.append("PRICE_MISSING")

        if (
            category.category == "DESKTOP_PC"
            and not category.pc_pricing_input_complete
        ):
            flags.append("PC_SPECS_INCOMPLETE")

        if observed != "RECENTLY_OBSERVED_UNVERIFIED":
            flags.append(observed)

        return {
            "platform": platform,
            "external_id": external_id,
            "title": title[:160],
            "url": listing.canonical_url,
            "category": category.category,
            "recorded_price_minor": price,
            "currency": currency,
            "source_status": status.value,
            "observation_freshness": observed,
            "risk_flags": sorted(set(flags)),
            "auto_valuation_allowed": False,
            "auto_buy_allowed": False,
        }

    except (
        TypeError,
        KeyError,
        AttributeError,
    ) as exc:
        raise ValueError("INVALID_RECORD") from exc


def audit(olx_db, facebook_db, limit=10000):
    sources = {
        "OLX": olx_db,
        "FACEBOOK": facebook_db,
    }

    source_count = Counter()
    categories = defaultdict(Counter)
    freshness_counts = defaultdict(Counter)
    gaps = defaultdict(Counter)
    rejected = Counter()
    combined = []

    for source, path in sources.items():
        for record in load_latest(path, limit):
            try:
                item = convert(source, record)
            except ValueError as exc:
                rejected[f"{source}:{exc}"] += 1
                continue

            combined.append(item)

            source_count[source] += 1
            categories[source][item["category"]] += 1
            freshness_counts[source][
                item["observation_freshness"]
            ] += 1

            for flag in item["risk_flags"]:
                gaps[source][flag] += 1

    combined.sort(
        key=lambda item: (
            item["platform"],
            item["external_id"],
        )
    )

    return {
        "total_unique_listings": len(combined),
        "by_platform": dict(source_count),
        "categories": {
            key: dict(value)
            for key, value in categories.items()
        },
        "observation_freshness": {
            key: dict(value)
            for key, value in freshness_counts.items()
        },
        "missing_evidence": {
            key: dict(value)
            for key, value in gaps.items()
        },
        "rejected_records": dict(rejected),
        "preview": combined[:20],
        "cross_platform_deduplication": "NOT_PERFORMED",
        "live_availability_verified": 0,
        "confirmed_sales": 0,
        "automatic_valuation_allowed": False,
        "automatic_buy_allowed": False,
        "source_databases_modified": False,
        "note": (
            "Wspolny katalog historycznych obserwacji. "
            "Nie oznacza aktualnie dostepnych ofert."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--olx", required=True)
    parser.add_argument("--facebook", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    safe = Path("/root/olx-shadow").resolve()

    paths = [
        Path(args.olx).resolve(),
        Path(args.facebook).resolve(),
        Path(args.report).resolve(),
    ]

    if not all(p.is_relative_to(safe) for p in paths):
        parser.error("Pliki musza byc w /root/olx-shadow")

    if paths[2] in paths[:2]:
        parser.error("Raport nie moze nadpisywac bazy")

    result = audit(paths[0], paths[1])

    paths[2].write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(
        {
            k: v
            for k, v in result.items()
            if k != "preview"
        },
        indent=2,
        ensure_ascii=False,
    ))

    print("REPORT:", paths[2])


if __name__ == "__main__":
    main()
