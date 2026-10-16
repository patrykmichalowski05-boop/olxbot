import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from .saved_searches_v1 import DB


def get_price_drops_report(path=DB, days=30, limit=50):
    path = Path(path)
    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=15
    ) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT h.search_id, h.listing_id,
                   h.old_price_zl, h.new_price_zl,
                   h.observed_utc, m.title, m.url,
                   m.asking_price_zl AS current_price,
                   m.last_seen_utc, m.match_status
            FROM saved_search_price_history h
            JOIN saved_search_matches m
              ON m.search_id=h.search_id
             AND m.source=h.source
             AND m.listing_id=h.listing_id
            WHERE h.event_kind='change'
              AND h.source='olx'
              AND h.old_price_zl > h.new_price_zl
              AND h.observed_utc >= ?
              AND m.match_status IN ('MATCH','REVIEW')
            ORDER BY h.id DESC
            LIMIT ?
        """, (cutoff, max(1, min(int(limit), 100)))).fetchall()

    items = []

    for row in rows:
        url = str(row["url"] or "")
        parsed = urlsplit(url)

        if (
            parsed.scheme != "https"
            or parsed.hostname not in ("olx.pl", "www.olx.pl")
        ):
            continue

        old = int(row["old_price_zl"])
        new = int(row["new_price_zl"])

        try:
            current = int(row["current_price"])
        except (TypeError, ValueError):
            current = None

        if old <= 0 or new <= 0:
            continue

        items.append({
            "search_id": row["search_id"],
            "listing_id": row["listing_id"],
            "title": row["title"],
            "url": url,
            "old_price": old,
            "new_price": new,
            "drop_zl": old - new,
            "drop_pct": round((old - new) / old * 100, 1),
            "current_price": current,
            "historical": current != new,
            "observed_utc": row["observed_utc"],
            "last_seen_utc": row["last_seen_utc"],
            "needs_review": row["match_status"] == "REVIEW"
        })

    return {
        "items": items,
        "total": len(items),
        "days": days
    }
