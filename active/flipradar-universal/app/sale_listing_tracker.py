import sqlite3

from datetime import (
    datetime,
    date,
)


DB_FILE = "/opt/olx-bot/deal_crm.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sale_listings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL UNIQUE,

            alert_id INTEGER,

            listed_price REAL NOT NULL,

            platform TEXT,

            listed_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            status TEXT NOT NULL
                DEFAULT 'ACTIVE'
        )
    """)

    conn.commit()
    conn.close()


def mark_listed(
    offer_key,
    alert_id,
    listed_price,
    platform="OLX",
):
    init_db()

    price = float(
        listed_price
    )

    if price <= 0:
        raise ValueError(
            "Nieprawidłowa cena"
        )

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    conn = connect()

    conn.execute("""
        INSERT INTO sale_listings (

            offer_key,
            alert_id,

            listed_price,
            platform,

            listed_at,
            updated_at,

            status
        )

        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')

        ON CONFLICT(offer_key)

        DO UPDATE SET

            alert_id = excluded.alert_id,

            listed_price =
                excluded.listed_price,

            platform =
                excluded.platform,

            updated_at =
                excluded.updated_at,

            status = 'ACTIVE'
    """, (
        offer_key,
        alert_id,
        price,
        platform,
        now,
        now,
    ))

    conn.commit()
    conn.close()


def get_listing(
    offer_key,
):
    init_db()

    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM sale_listings

        WHERE offer_key = ?
    """, (
        offer_key,
    )).fetchone()

    conn.close()

    return row


def days_listed(
    listing,
):
    if not listing:
        return 0

    raw = listing["listed_at"]

    try:
        listed = datetime.fromisoformat(
            raw
        ).date()

    except Exception:
        return 0

    return max(
        0,
        (
            date.today()
            - listed
        ).days,
    )


def price_advice(
    listing,
    minimum_price=None,
):
    if not listing:

        return {
            "days": 0,
            "status": "NOT_LISTED",
            "label": "Jeszcze niewystawiony",
            "suggested_price": None,
            "discount": 0,
        }


    days = days_listed(
        listing
    )

    current = float(
        listing["listed_price"]
    )

    minimum = (
        float(minimum_price)
        if minimum_price is not None
        else 0
    )


    if days < 7:

        return {
            "days": days,
            "status": "HOLD",
            "label":
                "ZOSTAW CENĘ — ZA WCZEŚNIE NA OBNIŻKĘ",

            "suggested_price":
                current,

            "discount":
                0,
        }


    if days < 14:
        discount = 100

    elif days < 21:
        discount = 150

    else:
        discount = 200


    suggested = max(
        minimum,
        current - discount,
    )


    if suggested >= current:

        return {
            "days": days,
            "status": "MINIMUM",
            "label":
                "JESTEŚ JUŻ PRZY CENIE MINIMALNEJ",

            "suggested_price":
                current,

            "discount":
                0,
        }


    return {
        "days": days,
        "status": "REDUCE",
        "label":
            "ROZWAŻ OBNIŻKĘ CENY",

        "suggested_price":
            suggested,

        "discount":
            current - suggested,
    }


def init_price_history():
    init_db()

    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sale_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            old_price REAL,
            new_price REAL NOT NULL,

            reason TEXT,
            changed_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sale_price_history_offer
        ON sale_price_history(
            offer_key,
            changed_at
        )
    """)

    conn.commit()
    conn.close()


def change_price(
    offer_key,
    new_price,
    reason="MANUAL",
):
    init_price_history()

    new_price = float(
        new_price
    )

    if new_price <= 0:
        raise ValueError(
            "Cena musi być większa od 0"
        )

    conn = connect()

    listing = conn.execute("""
        SELECT *
        FROM sale_listings
        WHERE offer_key = ?
    """, (
        offer_key,
    )).fetchone()

    if not listing:
        conn.close()

        raise ValueError(
            "Brak aktywnego ogłoszenia"
        )

    old_price = float(
        listing["listed_price"]
    )

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    conn.execute("""
        INSERT INTO sale_price_history (
            offer_key,
            old_price,
            new_price,
            reason,
            changed_at
        )

        VALUES (?, ?, ?, ?, ?)
    """, (
        offer_key,
        old_price,
        new_price,
        reason,
        now,
    ))

    conn.execute("""
        UPDATE sale_listings

        SET
            listed_price = ?,
            updated_at = ?

        WHERE offer_key = ?
    """, (
        new_price,
        now,
        offer_key,
    ))

    conn.commit()
    conn.close()


def price_history(
    offer_key,
    limit=30,
):
    init_price_history()

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM sale_price_history

        WHERE offer_key = ?

        ORDER BY
            changed_at DESC,
            id DESC

        LIMIT ?
    """, (
        offer_key,
        limit,
    )).fetchall()

    conn.close()

    return rows


def close_listing(
    offer_key,
):
    init_db()

    conn = connect()

    conn.execute("""
        UPDATE sale_listings

        SET
            status = 'SOLD',
            updated_at = ?

        WHERE offer_key = ?
    """, (
        datetime.now().isoformat(
            timespec="seconds"
        ),
        offer_key,
    ))

    conn.commit()
    conn.close()
