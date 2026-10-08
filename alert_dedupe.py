import hashlib
import re
import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/alert_history.db"


def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def ensure_column(
    conn,
    name,
    definition,
):

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(alerts)"
        ).fetchall()
    }

    if name not in columns:

        conn.execute(
            f"ALTER TABLE alerts "
            f"ADD COLUMN {name} {definition}"
        )


def init_db():

    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_key TEXT NOT NULL,
            price INTEGER,
            title TEXT,
            url TEXT,
            created_at TEXT NOT NULL
        )
    """)

    ensure_column(
        conn,
        "score",
        "INTEGER"
    )

    ensure_column(
        conn,
        "profit",
        "REAL"
    )

    ensure_column(
        conn,
        "quick_sale",
        "REAL"
    )

    ensure_column(
        conn,
        "total_cost",
        "REAL"
    )

    ensure_column(
        conn,
        "roi",
        "REAL"
    )

    ensure_column(
        conn,
        "mode",
        "TEXT"
    )

    ensure_column(
        conn,
        "trigger",
        "TEXT"
    )

    ensure_column(
        conn,
        "bundle",
        "INTEGER DEFAULT 0"
    )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_alert_offer_price
        ON alerts(
            offer_key,
            price
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_alert_created
        ON alerts(
            created_at
        )
    """)

    conn.commit()
    conn.close()


def normalize_price(value):

    try:

        return int(
            round(
                float(value)
            )
        )

    except Exception:

        return None


def number(value):

    try:

        if value is None:
            return None

        return float(value)

    except Exception:

        return None


def make_offer_key(
    details,
    offer_url,
):

    details = details or {}

    url = str(
        offer_url or ""
    )

    match = re.search(
        r"\bID[A-Za-z0-9]+\b",
        url,
        re.IGNORECASE,
    )

    if match:

        return (
            "OLX:"
            +
            match.group(0).upper()
        )

    if url:

        clean_url = (
            url.split(
                "?",
                1,
            )[0]
            .rstrip("/")
            .lower()
        )

        digest = hashlib.sha256(
            clean_url.encode(
                "utf-8"
            )
        ).hexdigest()[:24]

        return (
            "URL:"
            +
            digest
        )

    title = str(
        details.get(
            "title"
        )
        or ""
    ).lower()

    digest = hashlib.sha256(
        title.encode(
            "utf-8"
        )
    ).hexdigest()[:24]

    return (
        "TITLE:"
        +
        digest
    )



def already_sent(
    details,
    offer_url,
):
    """
    True = nie wysylaj ponownie.

    Ponowny alert dopuszczamy dopiero po spadku ceny
    o minimum 150 zl od ostatniego wyslanego alertu.
    """

    MIN_PRICE_DROP = 150

    init_db()

    offer_key = make_offer_key(
        details,
        offer_url,
    )

    price = normalize_price(
        (details or {}).get("price")
    )

    conn = connect()

    try:
        row = conn.execute("""
            SELECT price
            FROM alerts
            WHERE offer_key = ?
            ORDER BY id DESC
            LIMIT 1
        """, (offer_key,)).fetchone()
    finally:
        conn.close()

    # Brak wcześniejszego alertu.
    if row is None:
        return False

    last_price = row["price"]

    # Bez wiarygodnej ceny nie ponawiamy alertu.
    if price is None or last_price is None:
        return True

    try:
        current_price = int(price)
        previous_price = int(last_price)
    except (TypeError, ValueError):
        return True

    # Wzrost ceny i male obnizki nie generuja alertu.
    return (
        previous_price - current_price
    ) < MIN_PRICE_DROP


def record_alert(
    details,
    valuation,
    offer_url,
    score=None,
    mode=None,
):

    init_db()

    details = details or {}
    valuation = valuation or {}

    offer_key = make_offer_key(
        details,
        offer_url,
    )

    price = normalize_price(
        details.get(
            "price"
        )
    )

    profit = number(
        valuation.get(
            "profit"
        )
    )

    quick_sale = number(
        valuation.get(
            "quick_sale"
        )
    )

    total_cost = number(
        valuation.get(
            "total_cost"
        )
    )

    roi = None

    if (
        profit is not None
        and
        total_cost
        and
        total_cost > 0
    ):

        roi = (
            profit
            /
            total_cost
            *
            100
        )

    bundle = int(
        bool(
            valuation.get(
                "bundle_detected"
            )
        )
    )

    conn = connect()

    conn.execute("""
        INSERT INTO alerts (
            offer_key,
            price,
            title,
            url,
            created_at,
            score,
            profit,
            quick_sale,
            total_cost,
            roi,
            mode,
            trigger,
            bundle
        )

        VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?
        )
    """, (
        offer_key,
        price,
        str(
            details.get(
                "title"
            )
            or ""
        ),
        str(
            offer_url
            or ""
        ),
        datetime.now().isoformat(
            timespec="seconds"
        ),
        score,
        profit,
        quick_sale,
        total_cost,
        roi,
        mode,
        str(
            details.get(
                "_trigger"
            )
            or ""
        ),
        bundle,
    ))

    conn.commit()
    conn.close()


def stats():

    init_db()

    conn = connect()

    total = conn.execute("""
        SELECT COUNT(*)
        FROM alerts
    """).fetchone()[0]

    offers = conn.execute("""
        SELECT COUNT(
            DISTINCT offer_key
        )
        FROM alerts
    """).fetchone()[0]

    conn.close()

    return {
        "alerts": total,
        "offers": offers,
    }


if __name__ == "__main__":

    print(
        "ALERT HISTORY:",
        stats()
    )
