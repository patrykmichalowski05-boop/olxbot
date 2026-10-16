import math
import sqlite3

from .saved_searches_v1 import DB
from .market_snapshot_v1 import get_market_snapshot
from .flip_profit_settings_v1 import read_policy


def get_reserve():
    policy = read_policy()

    if not isinstance(policy, dict):
        return None

    keys = (
        "reserve_zl",
        "risk_reserve_zl",
        "reserve_cost_zl",
        "cost_reserve_zl",
        "cost_buffer_zl",
        "buffer_zl"
    )

    for key in keys:
        if key not in policy:
            continue

        try:
            value = float(
                str(policy[key]).replace(",", ".")
            )
            if math.isfinite(value) and 0 <= value <= 1000000:
                return value
        except (TypeError, ValueError):
            pass

    return None


def calculate_preview(price, reference, reserve, profit, roi):
    cost = price + reserve
    margin = reference - cost

    projected_roi = (
        margin / cost * 100
        if cost > 0 else 0
    )

    limit_profit = reference - reserve - profit

    limit_roi = (
        reference / (1 + roi / 100)
        - reserve
    )

    max_buy = max(
        0,
        math.floor(min(limit_profit, limit_roi))
    )

    return {
        "margin_zl": round(margin),
        "roi_pct": round(projected_roi, 1),
        "max_buy_zl": max_buy,
        "meets_target": (
            margin >= profit
            and projected_roi >= roi
        )
    }


def get_financial_rows(search):
    market = get_market_snapshot(search["id"])
    reserve = get_reserve()

    q1 = (
        market["low_zl"]
        if market["available"]
        else None
    )

    with sqlite3.connect(
        DB.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=10
    ) as db:
        rows = db.execute("""
            SELECT url, asking_price_zl, match_status
            FROM saved_search_matches
            WHERE search_id=?
              AND source='olx'
              AND match_status IN ('MATCH','REVIEW')
        """, (search["id"],)).fetchall()

    results = {}

    for url, price, status in rows:
        price = int(price)

        entry = {
            "label": "Za malo danych",
            "difference_pct": None,
            "scenario": None,
            "reserve_available": reserve is not None
        }

        if q1 and q1 > 0:
            difference = round(
                (q1 - price) / q1 * 100, 1
            )

            entry["difference_pct"] = difference

            if price < q1 * 0.65:
                entry["label"] = (
                    "Wyjatkowo niska cena - "
                    "wymaga szczegolnej weryfikacji"
                )
            elif price < q1:
                entry["label"] = (
                    "Cena ponizej dolnego kwartyla OLX"
                )
            else:
                entry["label"] = (
                    "Brak wyraznej przewagi nad Q1"
                )

            if status == "REVIEW":
                entry["label"] = (
                    "DO SPRAWDZENIA - "
                    "mozliwy problem ze sprzetem"
                )

            if (
                reserve is not None
                and market["quality"] == "wstepna"
            ):
                entry["scenario"] = calculate_preview(
                    price=price,
                    reference=q1,
                    reserve=reserve,
                    profit=float(search["min_profit_zl"]),
                    roi=float(search["min_roi_pct"])
                )

        results[url] = entry

    return results
