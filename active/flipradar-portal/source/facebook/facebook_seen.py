import re
import sqlite3

from datetime import datetime, timezone
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent
    / "facebook_seen.db"
)


def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def extract_listing_id(url):
    if not url:
        return None

    match = re.search(
        r"/marketplace/item/(\d+)",
        url
    )

    if not match:
        return None

    return match.group(1)


def connect():
    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    with connect() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facebook_offers (
                listing_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                price INTEGER,
                old_price INTEGER,
                location TEXT,

                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,

                seen_count INTEGER NOT NULL DEFAULT 1,

                analyzed INTEGER NOT NULL DEFAULT 0,

                last_profit INTEGER,
                last_quick_sale INTEGER
            )
            """
        )

        conn.commit()


def observe_offer(
    url,
    title=None,
    price=None,
    old_price=None,
    location=None,
):
    listing_id = extract_listing_id(
        url
    )

    if not listing_id:
        return {
            "ok": False,
            "reason": "Brak listing_id"
        }

    now = now_iso()

    with connect() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM facebook_offers
            WHERE listing_id = ?
            """,
            (listing_id,)
        ).fetchone()

        # --------------------------------------------
        # NOWA OFERTA
        # --------------------------------------------

        if row is None:

            conn.execute(
                """
                INSERT INTO facebook_offers (
                    listing_id,
                    url,
                    title,
                    price,
                    old_price,
                    location,
                    first_seen,
                    last_seen,
                    seen_count,
                    analyzed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
                """,
                (
                    listing_id,
                    url,
                    title,
                    price,
                    old_price,
                    location,
                    now,
                    now,
                )
            )

            conn.commit()

            return {
                "ok": True,
                "new": True,
                "listing_id": listing_id,
                "seen_count": 1,
            }

        # --------------------------------------------
        # ZNANA OFERTA
        # --------------------------------------------

        # RETRY_AFTER_PRICE_CHANGE_V1
        price_changed = (
            price is not None
            and price != row["price"]
        )

        # Brak ceny na karcie nie usuwa ostatniej znanej ceny.
        if price is None:
            price = row["price"]

        # Błąd analizy lub Telegrama pozostawi analyzed = 0.
        if price_changed:
            conn.execute(
                "UPDATE facebook_offers "
                "SET analyzed = 0 WHERE listing_id = ?",
                (listing_id,),
            )

        new_seen_count = (
            row["seen_count"] + 1
        )

        conn.execute(
            """
            UPDATE facebook_offers
            SET
                url = ?,
                title = ?,
                price = ?,
                old_price = ?,
                location = ?,
                last_seen = ?,
                seen_count = ?
            WHERE listing_id = ?
            """,
            (
                url,
                title,
                price,
                old_price,
                location,
                now,
                new_seen_count,
                listing_id,
            )
        )

        conn.commit()

        return {
            "ok": True,
            "new": False,
            "listing_id": listing_id,
            "seen_count": new_seen_count,
            "analyzed": (
                bool(row["analyzed"])
                and not price_changed
            ),
            "previous_price":
                row["price"],
        }


def mark_analyzed(
    listing_id,
    profit=None,
    quick_sale=None,
):
    with connect() as conn:

        conn.execute(
            """
            UPDATE facebook_offers
            SET
                analyzed = 1,
                last_profit = ?,
                last_quick_sale = ?
            WHERE listing_id = ?
            """,
            (
                profit,
                quick_sale,
                listing_id,
            )
        )

        conn.commit()


def get_offer(listing_id):
    with connect() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM facebook_offers
            WHERE listing_id = ?
            """,
            (listing_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)


def mark_all_as_analyzed():
    with connect() as conn:

        conn.execute(
            """
            UPDATE facebook_offers
            SET analyzed = 1
            """
        )

        conn.commit()


def mark_alert_sent(
    listing_id,
    price,
    profit,
):
    now = now_iso()

    with connect() as conn:

        conn.execute(
            """
            UPDATE facebook_offers
            SET
                alert_sent = 1,
                last_alert_price = ?,
                last_alert_profit = ?,
                last_alert_at = ?
            WHERE listing_id = ?
            """,
            (
                price,
                profit,
                now,
                listing_id,
            )
        )

        conn.commit()


def ensure_alert_columns():
    """
    Zapewnia istnienie pól odpowiedzialnych
    za pamięć wysłanych alertów Telegram.
    """

    required = {
        "alert_sent":
            "INTEGER NOT NULL DEFAULT 0",

        "last_alert_price":
            "INTEGER",

        "last_alert_profit":
            "INTEGER",

        "last_alert_at":
            "TEXT",
    }

    with connect() as conn:

        existing = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(facebook_offers)"
            )
        }

        for column, definition in required.items():

            if column in existing:
                continue

            conn.execute(
                f"""
                ALTER TABLE facebook_offers
                ADD COLUMN {column} {definition}
                """
            )

        conn.commit()
