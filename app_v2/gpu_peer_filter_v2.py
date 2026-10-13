import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median, quantiles

from .saved_searches_v1 import DB
from .gpu_attributes_v1 import analyze


def remove_outliers(prices):
    prices = sorted(prices)

    if len(prices) < 4:
        return prices, []

    q1, _, q3 = quantiles(
        prices, n=4, method="inclusive"
    )

    iqr = q3 - q1
    lower = max(1, q1 - 1.5 * iqr)
    upper = q3 + 1.5 * iqr

    kept = [x for x in prices if lower <= x <= upper]
    rejected = [x for x in prices if x < lower or x > upper]

    return kept, rejected


def evaluate(search, path=DB, days=14):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=15
    ) as db:
        rows = db.execute("""
            SELECT listing_id, title, url,
                   asking_price_zl, match_status,
                   last_seen_utc
            FROM saved_search_matches
            WHERE search_id=? AND source='olx'
              AND match_status IN ('MATCH','REVIEW')
        """, (search["id"],)).fetchall()

    offers = []

    for lid, title, url, price, status, seen in rows:
        try:
            price = int(price)
            date = datetime.fromisoformat(
                seen.replace("Z", "+00:00")
            )

            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

            if price <= 0 or date < cutoff:
                continue
        except (TypeError, ValueError, AttributeError):
            continue

        offers.append({
            "id": lid,
            "url": url,
            "price": price,
            "status": status,
            "attributes": analyze(title)
        })

    report = {}

    for target in offers:
        target_attr = target["attributes"]

        peers = []

        for other in offers:
            attr = other["attributes"]

            if other["id"] == target["id"]:
                continue

            if other["status"] != "MATCH":
                continue

            if attr["model"] != target_attr["model"]:
                continue

            if attr["model"] == "nieustalony":
                continue

            if attr["condition"] != target_attr["condition"]:
                continue

            a = attr["vram_gb"]
            b = target_attr["vram_gb"]

            if a and b and a != b:
                continue

            peers.append(other["price"])

        clean, outliers = remove_outliers(peers)

        enough = len(clean) >= 5

        report[target["url"]] = {
            "model": target_attr["model"],
            "condition": target_attr["condition"],
            "before_filter": len(peers),
            "peer_count": len(clean),
            "excluded_prices": outliers,
            "available": enough,
            "median_zl": round(median(clean)) if enough else None,
            "indicative_median_zl": (
                round(median(clean))
                if len(clean) >= 3 else None
            ),
            "financial_preview_allowed": (
                enough
                and target["status"] == "MATCH"
            ),
            "warning": (
                "Wycena wymaga minimum 5 ofert tego samego "
                "modelu i tej samej kategorii stanu"
                if not enough
                else "Ceny ofertowe, bez potwierdzenia sprzedazy"
            )
        }

    return report
