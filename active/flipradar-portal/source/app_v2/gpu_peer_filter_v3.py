import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from .saved_searches_v1 import DB
from .gpu_attributes_v1 import analyze
from .gpu_listing_guard_v2 import assess
from .gpu_peer_filter_v2 import remove_outliers
from .peer_valuation_v1 import parse_time


def evaluate(search, path=DB, days=14):
    # V3 na razie obsluguje tylko profil RTX 5060.
    if (
        search.get("category") != "gpu"
        or analyze(search.get("query_text"))["model"] != "RTX 5060"
    ):
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=20
    ) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT listing_id, title, url,
                   asking_price_zl, match_status,
                   last_seen_utc
            FROM saved_search_matches
            WHERE search_id=?
              AND source='olx'
              AND match_status IN ('MATCH','REVIEW')
        """, (search["id"],)).fetchall()

    offers = []

    for row in rows:
        try:
            price = int(row["asking_price_zl"])
        except (TypeError, ValueError):
            continue

        seen = parse_time(row["last_seen_utc"])

        if not seen or seen < cutoff or price <= 0:
            continue

        guard = assess(row["title"])

        offers.append({
            "id": row["listing_id"],
            "url": row["url"],
            "price": price,
            "status": row["match_status"],
            "guard": guard,
            "attrs": guard["attributes"]
        })

    valid_peers = [
        x for x in offers
        if x["status"] == "MATCH"
        and x["guard"]["status"] == "STANDALONE_GPU"
    ]

    report = {}

    for target in offers:
        attrs = target["attrs"]
        guard = target["guard"]

        peers = []

        if guard["status"] == "STANDALONE_GPU":
            for other in valid_peers:
                if other["id"] == target["id"]:
                    continue

                other_attrs = other["attrs"]

                if other_attrs["model"] != attrs["model"]:
                    continue

                if other_attrs["condition"] != attrs["condition"]:
                    continue

                a = attrs["vram_gb"]
                b = other_attrs["vram_gb"]

                if a is not None and b is not None and a != b:
                    continue

                peers.append(other["price"])

        clean, excluded = remove_outliers(peers)

        enough = (
            guard["status"] == "STANDALONE_GPU"
            and target["status"] == "MATCH"
            and len(clean) >= 5
        )

        reason = (
            "Tytul nie potwierdza samodzielnej karty GPU"
            if guard["status"] != "STANDALONE_GPU"
            else "Za malo porownywalnych ofert"
            if not enough
            else "Ceny wystawienia, bez danych transakcyjnych"
        )

        report[target["url"]] = {
            "model": attrs["model"],
            "condition": attrs["condition"],
            "before_filter": len(peers),
            "peer_count": len(clean),
            "excluded_prices": excluded,
            "available": enough,
            "median_zl": round(median(clean)) if enough else None,
            "indicative_median_zl": (
                round(median(clean)) if len(clean) >= 3 else None
            ),
            "financial_preview_allowed": False,
            "warning": reason,
            "listing_status": guard["status"],
            "listing_reason": guard["reason"]
        }

    return report
