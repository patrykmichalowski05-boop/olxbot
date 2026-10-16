import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .saved_searches_v1 import DB

STATUSES = {"interest", "checked", "rejected", "pending"}


def connect(path=DB, readonly=False):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Brak bazy SQLite")
    if readonly:
        return sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=15
        )
    return sqlite3.connect(path, timeout=15)


def initialize(path=DB):
    with connect(path) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS review_decisions (
                search_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                decision TEXT NOT NULL
                    CHECK(decision IN (
                        'interest','checked','rejected'
                    )),
                updated_utc TEXT NOT NULL,
                PRIMARY KEY(search_id,source,listing_id)
            )
        """)


def set_decision(search_id, listing_id, decision, path=DB):
    if decision not in STATUSES:
        raise ValueError("Nieprawidlowa decyzja")

    listing_id = str(listing_id or "").strip()
    if not listing_id or len(listing_id) > 120:
        raise ValueError("Nieprawidlowy identyfikator")

    with connect(path) as db:
        exists = db.execute("""
            SELECT 1 FROM saved_search_matches
            WHERE search_id=? AND source='olx'
              AND listing_id=?
              AND match_status IN ('MATCH','REVIEW')
        """, (search_id, listing_id)).fetchone()

        if not exists:
            raise ValueError("Nie znaleziono oferty")

        if decision == "pending":
            db.execute("""
                DELETE FROM review_decisions
                WHERE search_id=? AND source='olx'
                  AND listing_id=?
            """, (search_id, listing_id))
        else:
            db.execute("""
                INSERT INTO review_decisions
                (search_id,source,listing_id,decision,updated_utc)
                VALUES (?, 'olx', ?, ?, ?)
                ON CONFLICT(search_id,source,listing_id)
                DO UPDATE SET
                    decision=excluded.decision,
                    updated_utc=excluded.updated_utc
            """, (
                search_id, listing_id, decision,
                datetime.now(timezone.utc).isoformat()
            ))


def prepare_queue(report, path=DB):
    with connect(path, readonly=True) as db:
        rows = db.execute("""
            SELECT m.search_id, m.url, m.listing_id,
                   d.decision
            FROM saved_search_matches m
            LEFT JOIN review_decisions d
              ON d.search_id=m.search_id
             AND d.source=m.source
             AND d.listing_id=m.listing_id
            WHERE m.source='olx'
        """).fetchall()

    lookup = {
        (sid, url): (listing_id, decision)
        for sid, url, listing_id, decision in rows
    }

    pending = []
    handled = []

    for original in report["items"]:
        item = dict(original)
        key = (item["search_id"], item["url"])

        if key not in lookup:
            continue

        listing_id, decision = lookup[key]
        item["listing_id"] = listing_id
        item["decision"] = decision

        if decision:
            handled.append(item)
        else:
            pending.append(item)

    return {
        **report,
        "items": pending,
        "total": len(pending),
        "handled": handled,
        "handled_total": len(handled)
    }
