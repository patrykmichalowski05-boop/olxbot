import sqlite3
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .saved_searches_v1 import DB


def get_market_snapshot(search_id, days=14, path=DB):
    path = Path(path)

    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Nieprawidlowa baza cen")

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    ).isoformat()

    uri = path.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True, timeout=10) as db:
        rows = db.execute("""
            SELECT asking_price_zl
            FROM saved_search_matches
            WHERE search_id=?
              AND source='olx'
              AND match_status='MATCH'
              AND last_seen_utc >= ?
              AND asking_price_zl > 0
              AND asking_price_zl <= 10000000
        """, (search_id, cutoff)).fetchall()

    prices = sorted(int(row[0]) for row in rows)
    count = len(prices)

    result = {
        "count": count,
        "days": days,
        "available": False,
        "median_zl": None,
        "low_zl": None,
        "high_zl": None,
        "minimum_zl": None,
        "maximum_zl": None,
        "quality": "brak_danych",
    }

    if count < 5:
        return result

    median = statistics.median(prices)
    low = prices[(count - 1) // 4]
    high = prices[(3 * (count - 1)) // 4]

    spread = (
        (high - low) / median
        if median > 0 else 999
    )

    result.update({
        "available": True,
        "median_zl": round(median),
        "low_zl": low,
        "high_zl": high,
        "minimum_zl": prices[0],
        "maximum_zl": prices[-1],
        "quality": (
            "wstepna"
            if spread <= 0.6
            else "duza_rozbieznosc"
        ),
    })

    return result
