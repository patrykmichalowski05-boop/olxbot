import sqlite3
from datetime import datetime, timedelta


DB_FILE = "/opt/olx-bot/deal_crm.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS followups (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            alert_id INTEGER,

            title TEXT,
            url TEXT,

            due_at TEXT NOT NULL,
            note TEXT,

            status TEXT NOT NULL
                DEFAULT 'ACTIVE',

            notified_at TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_followups_status_due
        ON followups(
            status,
            due_at
        )
    """)

    conn.commit()
    conn.close()


def create_followup(
    offer_key,
    alert_id,
    title,
    url,
    due_at,
    note=None,
):
    init_db()

    conn = connect()

    # Jedna aktywna przypominajka
    # na daną ofertę.
    conn.execute("""
        UPDATE followups

        SET
            status = 'CANCELLED',
            completed_at = ?

        WHERE
            offer_key = ?
            AND status = 'ACTIVE'
    """, (
        datetime.now().isoformat(
            timespec="seconds"
        ),
        offer_key,
    ))

    conn.execute("""
        INSERT INTO followups (

            offer_key,
            alert_id,

            title,
            url,

            due_at,
            note,

            status,

            created_at
        )

        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            'ACTIVE',
            ?
        )
    """, (
        offer_key,
        alert_id,
        title,
        url,
        due_at,
        note,
        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()
    conn.close()


def schedule_from_mode(
    mode,
):
    now = datetime.now()

    if mode == "1h":
        return (
            now
            +
            timedelta(hours=1)
        )

    if mode == "3h":
        return (
            now
            +
            timedelta(hours=3)
        )

    if mode == "tomorrow":
        tomorrow = (
            now
            +
            timedelta(days=1)
        )

        return tomorrow.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

    raise ValueError(
        "Nieznany tryb follow-up."
    )


def active_for_offer(
    offer_key,
):
    init_db()

    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM followups

        WHERE
            offer_key = ?
            AND status = 'ACTIVE'

        ORDER BY id DESC

        LIMIT 1
    """, (
        offer_key,
    )).fetchone()

    conn.close()

    return row


def complete(
    followup_id,
):
    init_db()

    conn = connect()

    conn.execute("""
        UPDATE followups

        SET
            status = 'DONE',
            completed_at = ?

        WHERE id = ?
    """, (
        datetime.now().isoformat(
            timespec="seconds"
        ),
        followup_id,
    ))

    conn.commit()
    conn.close()


def cancel(
    followup_id,
):
    init_db()

    conn = connect()

    conn.execute("""
        UPDATE followups

        SET
            status = 'CANCELLED',
            completed_at = ?

        WHERE id = ?
    """, (
        datetime.now().isoformat(
            timespec="seconds"
        ),
        followup_id,
    ))

    conn.commit()
    conn.close()
