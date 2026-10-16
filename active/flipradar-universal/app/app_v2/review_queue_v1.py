import sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit

from .saved_searches_v1 import DB, all_searches
from .market_snapshot_v1 import get_market_snapshot


def classify(status, price, q1):
    if status == "REVIEW":
        return 0, "Niepewny stan techniczny"

    if not q1 or price <= 0:
        return None

    ratio = price / q1

    if ratio < 0.65:
        return 1, "Podejrzanie niska cena"

    if ratio < 0.85:
        return 2, "Cena wyraznie ponizej Q1"

    return None


def get_review_queue():
    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=14)
    ).isoformat()

    searches = {
        s["id"]: s
        for s in all_searches()
    }

    uri = DB.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT search_id, title, url,
                   asking_price_zl, match_status,
                   match_reason, first_seen_utc,
                   last_seen_utc
            FROM saved_search_matches
            WHERE source='olx'
              AND match_status IN ('MATCH','REVIEW')
              AND last_seen_utc >= ?
            ORDER BY last_seen_utc DESC
            LIMIT 2000
        """, (cutoff,)).fetchall()

    snapshots = {}
    items = []

    for row in rows:
        s = searches.get(row["search_id"])

        if not s:
            continue

        url = urlsplit(row["url"])

        if (
            url.scheme != "https"
            or url.hostname not in ("olx.pl", "www.olx.pl")
        ):
            continue

        sid = s["id"]

        if sid not in snapshots:
            snapshots[sid] = get_market_snapshot(sid)

        market = snapshots[sid]
        q1 = market["low_zl"] if market["available"] else None

        result = classify(
            row["match_status"],
            row["asking_price_zl"],
            q1
        )

        if result is None:
            continue

        priority, reason = result

        items.append({
            "search_id": sid,
            "search_name": s["name"],
            "title": row["title"],
            "url": row["url"],
            "price": row["asking_price_zl"],
            "q1": q1,
            "sample": market["count"],
            "priority": priority,
            "reason": row["match_reason"] or reason
                if priority == 0 else reason,
            "difference": (
                round((q1 - row["asking_price_zl"]) / q1 * 100, 1)
                if q1 else None
            ),
            "first_seen": row["first_seen_utc"],
            "last_seen": row["last_seen_utc"]
        })

    items.sort(key=lambda x: x["last_seen"], reverse=True)
    items.sort(key=lambda x: x["priority"])

    return {
        "items": items[:100],
        "total": len(items),
        "suspicious": sum(x["priority"] == 1 for x in items),
        "technical": sum(x["priority"] == 0 for x in items)
    }
