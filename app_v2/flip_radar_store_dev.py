import math
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from .flip_profit_settings_v1 import read_policy

DB = Path(
    "/opt/olx-bot-ui-dev/data/flip_radar_dev.sqlite3"
)


def connection():
    if DB.is_symlink() or not DB.is_file():
        raise RuntimeError("Nieprawidlowa baza Flip Radar")

    uri = DB.resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def safe_url(value):
    try:
        u = urlsplit(str(value or ""))
        host = (u.hostname or "").lower()

        accepted = (
            host == "olx.pl"
            or host.endswith(".olx.pl")
            or host == "facebook.com"
            or host.endswith(".facebook.com")
        )

        if u.scheme != "https" or not accepted:
            return None

        return value
    except ValueError:
        return None


def min_resale(price, policy=None):
    if not isinstance(price, int) or price <= 0:
        return None

    from decimal import Decimal, ROUND_CEILING

    if policy is None:
        policy = read_policy()

    total = price + policy["reserve_zl"]

    profit_target = total + policy["min_profit_zl"]

    roi_multiplier = (
        Decimal("1")
        + Decimal(str(policy["min_roi_pct"]))
        / Decimal("100")
    )

    roi_target = int(
        (
            Decimal(total) * roi_multiplier
        ).to_integral_value(rounding=ROUND_CEILING)
    )

    return max(profit_target, roi_target)


def summary():
    with connection() as db:
        result = dict(db.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN source='olx'
                    THEN 1 ELSE 0 END) AS olx,
                SUM(CASE WHEN source='facebook'
                    THEN 1 ELSE 0 END) AS facebook,
                SUM(CASE WHEN price_zl > 1500
                    THEN 1 ELSE 0 END) AS over_1500
            FROM offers
        """).fetchone())

        result["price_changes"] = db.execute(
            "SELECT COUNT(*) FROM price_events"
        ).fetchone()[0]

        result["last_import_utc"] = db.execute(
            "SELECT MAX(imported_utc) FROM imports"
        ).fetchone()[0]

    return result


def search_offers(
    q="",
    source="",
    sort="recent",
    page=1,
    page_size=30
):
    if source not in ("", "olx", "facebook"):
        raise ValueError("Nieprawidlowe zrodlo")

    if sort not in ("recent", "cheap", "expensive"):
        raise ValueError("Nieprawidlowe sortowanie")

    if not 1 <= page <= 100000:
        raise ValueError("Nieprawidlowa strona")

    if not 1 <= page_size <= 100:
        raise ValueError("Nieprawidlowy rozmiar strony")

    q = str(q or "").strip()[:100]

    conditions = []
    args = []

    if source:
        conditions.append("source=?")
        args.append(source)

    if q:
        pattern = "%" + (
            q.replace("!", "!!")
             .replace("%", "!%")
             .replace("_", "!_")
        ) + "%"

        conditions.append("""
            (
                title LIKE ? ESCAPE '!'
                OR cpu LIKE ? ESCAPE '!'
                OR gpu LIKE ? ESCAPE '!'
                OR listing_id LIKE ? ESCAPE '!'
            )
        """)

        args.extend([pattern] * 4)

    where = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    order = {
        "recent": "last_seen_utc DESC",
        "cheap": "price_zl IS NULL, price_zl ASC",
        "expensive": "price_zl DESC",
    }[sort]

    with connection() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM offers" + where,
            args
        ).fetchone()[0]

        sql = """
            SELECT source, listing_id, title, url,
                   price_zl, cpu, gpu, ram_gb,
                   status, detail_status,
                   technical_review, financial_status,
                   last_seen_utc
            FROM offers
        """ + where + " ORDER BY " + order + """
            LIMIT ? OFFSET ?
        """

        rows = db.execute(
            sql,
            args + [page_size, (page - 1) * page_size]
        ).fetchall()

    items = []
    profit_policy = read_policy()

    for row in rows:
        item = dict(row)
        item["url"] = safe_url(item["url"])
        item["minimum_resale_needed_zl"] = min_resale(
            item["price_zl"],
            profit_policy
        )

        item["profit_verified"] = False
        item["availability_verified"] = False

        items.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size),
        "items": items,
    }


def price_history(source, listing_id):
    if source not in ("olx", "facebook"):
        raise ValueError("Nieprawidlowe zrodlo")

    ident = str(listing_id).upper()

    if not 3 <= len(ident) <= 40 or not ident.isalnum():
        raise ValueError("Nieprawidlowe ID")

    with connection() as db:
        rows = db.execute("""
            SELECT old_price, new_price, observed_utc
            FROM price_events
            WHERE source=? AND listing_id=?
            ORDER BY observed_utc DESC
            LIMIT 100
        """, (source, ident)).fetchall()

    return [dict(x) for x in rows]
