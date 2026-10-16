import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median, quantiles

from .saved_searches_v1 import DB
from .profit_preview_v1 import calculate_preview, get_reserve


def parse_time(value):
    try:
        dt = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def evaluate_search(search, path=DB, days=14):
    path = Path(path)

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    with sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=15
    ) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT listing_id, url, title,
                   asking_price_zl, match_status,
                   last_seen_utc
            FROM saved_search_matches
            WHERE search_id=?
              AND source='olx'
              AND match_status IN ('MATCH','REVIEW')
            LIMIT 4000
        """, (search["id"],)).fetchall()

    offers = []

    for row in rows:
        try:
            price = int(row["asking_price_zl"])
        except (ValueError, TypeError):
            continue

        seen = parse_time(row["last_seen_utc"])

        if not seen or seen < cutoff or price <= 0:
            continue

        offers.append({
            "id": row["listing_id"],
            "url": row["url"],
            "price": price,
            "status": row["match_status"],
        })

    reserve = get_reserve()
    result = {}

    for offer in offers:
        # Porownania tylko z INNYMI ofertami MATCH.
        peers = sorted(
            x["price"] for x in offers
            if x["id"] != offer["id"]
            and x["status"] == "MATCH"
        )

        entry = {
            "available": False,
            "peer_count": len(peers),
            "confidence": "brak danych",
            "q1_zl": None,
            "median_zl": None,
            "difference_pct": None,
            "verdict": "Za malo porownywalnych ofert",
            "scenario": None,
        }

        if len(peers) < 5:
            result[offer["url"]] = entry
            continue

        q1, _, q3 = quantiles(
            peers, n=4, method="inclusive"
        )

        typical = median(peers)
        difference = (
            (q1 - offer["price"]) / q1 * 100
        )
        ratio = offer["price"] / q1

        spread = (
            (q3 - q1) / typical
            if typical else 1
        )

        confidence = (
            "umiarkowana"
            if len(peers) >= 10 and spread <= 0.35
            else "ograniczona"
        )

        if offer["status"] == "REVIEW":
            verdict = "Stan techniczny do weryfikacji"
        elif ratio < 0.65:
            verdict = "Nietypowo niska cena - sprawdz dokladnie"
        elif ratio < 0.85:
            verdict = "Wyraznie ponizej cen porownawczych"
        elif ratio < 1:
            verdict = "Ponizej dolnego kwartyla"
        else:
            verdict = "Brak wyraznej przewagi cenowej"

        scenario = None

        if reserve is not None and offer["status"] == "MATCH":
            scenario = calculate_preview(
                price=offer["price"],
                reference=q1,
                reserve=reserve,
                profit=float(search["min_profit_zl"]),
                roi=float(search["min_roi_pct"])
            )

        entry.update({
            "available": True,
            "q1_zl": round(q1),
            "median_zl": round(typical),
            "difference_pct": round(difference, 1),
            "confidence": confidence,
            "verdict": verdict,
            "scenario": scenario,
        })

        result[offer["url"]] = entry

    return result
