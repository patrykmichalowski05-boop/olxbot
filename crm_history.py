import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/deal_crm.db"


VALID_KINDS = {
    "NOTE",
    "MESSAGE",
    "MY_OFFER",
    "SELLER_OFFER",
}


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS deal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            alert_id INTEGER,

            kind TEXT NOT NULL,

            amount REAL,
            note TEXT,

            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_deal_history_offer
        ON deal_history(
            offer_key,
            created_at
        )
    """)

    conn.commit()
    conn.close()


def add_entry(
    offer_key,
    alert_id,
    kind,
    amount=None,
    note=None,
):
    init_db()

    kind = str(
        kind or ""
    ).upper()

    if kind not in VALID_KINDS:
        raise ValueError(
            "Nieprawidłowy typ wpisu"
        )

    if amount in ("", None):
        amount = None
    else:
        amount = float(amount)

    note = (
        str(note).strip()
        if note
        else None
    )

    conn = connect()

    conn.execute("""
        INSERT INTO deal_history (
            offer_key,
            alert_id,
            kind,
            amount,
            note,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        offer_key,
        alert_id,
        kind,
        amount,
        note,
        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()
    conn.close()


def history_for_offer(
    offer_key,
    limit=50,
):
    init_db()

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM deal_history

        WHERE offer_key = ?

        ORDER BY
            created_at DESC,
            id DESC

        LIMIT ?
    """, (
        offer_key,
        limit,
    )).fetchall()

    conn.close()

    return rows
