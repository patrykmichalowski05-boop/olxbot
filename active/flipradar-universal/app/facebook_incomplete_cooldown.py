import sqlite3
import time
from contextlib import closing
from pathlib import Path

DB_FILE = str(
    Path(__file__).resolve().parent
    / "facebook_incomplete_retry.db"
)

RETRY_SECONDS = 24 * 3600


def normalized(title, price):
    return (
        str(title or "").strip(),
        "" if price is None else str(price).strip(),
    )


def connect():
    db = sqlite3.connect(DB_FILE, timeout=10)
    db.execute("""
        CREATE TABLE IF NOT EXISTS incomplete (
            listing_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            price TEXT NOT NULL,
            missing TEXT,
            retry_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    db.commit()
    return db


def cooldown_remaining(listing_id, title, price):
    try:
        with closing(connect()) as db:
            row = db.execute("""
                SELECT title, price, retry_at
                FROM incomplete
                WHERE listing_id = ?
            """, (str(listing_id),)).fetchone()

        if row is None:
            return 0

        current = normalized(title, price)

        if (row[0], row[1]) != current:
            return 0

        return max(0, int(row[2] - time.time()))

    except sqlite3.Error as exc:
        print("[FB COOLDOWN DB ERROR]", exc)
        return 0


def note_incomplete(listing_id, title, price, missing):
    now = time.time()
    title, price = normalized(title, price)

    try:
        with closing(connect()) as db:
            db.execute("""
                INSERT INTO incomplete
                (listing_id, title, price, missing, retry_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                    title = excluded.title,
                    price = excluded.price,
                    missing = excluded.missing,
                    retry_at = excluded.retry_at,
                    updated_at = excluded.updated_at
            """, (
                str(listing_id),
                title,
                price,
                ",".join(missing),
                now + RETRY_SECONDS,
                now,
            ))
            db.commit()

    except sqlite3.Error as exc:
        print("[FB COOLDOWN DB ERROR]", exc)


def clear_incomplete(listing_id):
    try:
        with closing(connect()) as db:
            db.execute(
                "DELETE FROM incomplete WHERE listing_id = ?",
                (str(listing_id),),
            )
            db.commit()

    except sqlite3.Error as exc:
        print("[FB COOLDOWN DB ERROR]", exc)
