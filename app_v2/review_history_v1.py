import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from .saved_searches_v1 import DB
from .review_notes_v1 import STATUSES


def initialize(path=DB):
    path = Path(path)

    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Brak bazy SQLite")

    with sqlite3.connect(path, timeout=15) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS review_note_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                seller_name TEXT NOT NULL,
                contact_status TEXT NOT NULL,
                note_text TEXT NOT NULL,
                event_kind TEXT NOT NULL,
                created_utc TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_history
            ON review_note_history (
                search_id, source, listing_id, id
            )
        """)

        db.execute("""
            INSERT INTO review_note_history (
                search_id, source, listing_id,
                seller_name, contact_status,
                note_text, event_kind, created_utc
            )
            SELECT
                n.search_id, n.source, n.listing_id,
                n.seller_name, n.contact_status,
                n.note_text, 'import', n.updated_utc
            FROM review_notes n
            WHERE NOT EXISTS (
                SELECT 1 FROM review_note_history h
                WHERE h.search_id=n.search_id
                  AND h.source=n.source
                  AND h.listing_id=n.listing_id
            )
        """)


def save_with_history(
    search_id, listing_id, seller_name,
    contact_status, note_text, path=DB
):
    try:
        sid = int(search_id)
    except (ValueError, TypeError):
        raise ValueError("Nieprawidlowy profil")

    lid = str(listing_id or "").strip()
    seller = str(seller_name or "").strip()
    status = str(contact_status or "none").strip()
    note = str(note_text or "").strip()

    if sid < 1 or not 1 <= len(lid) <= 120:
        raise ValueError("Nieprawidlowa oferta")

    if status not in STATUSES:
        raise ValueError("Nieznany status")

    if len(seller) > 120 or len(note) > 3000:
        raise ValueError("Zbyt dlugi tekst")

    initialize(path)
    stamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(path, timeout=15) as db:
        db.execute("BEGIN IMMEDIATE")

        exists = db.execute("""
            SELECT 1 FROM saved_search_matches
            WHERE search_id=? AND source='olx'
              AND listing_id=?
              AND match_status IN ('MATCH','REVIEW')
        """, (sid, lid)).fetchone()

        if not exists:
            raise ValueError("Nie znaleziono oferty")

        previous = db.execute("""
            SELECT seller_name, contact_status, note_text
            FROM review_notes
            WHERE search_id=? AND source='olx'
              AND listing_id=?
        """, (sid, lid)).fetchone()

        if previous == (seller, status, note):
            return False

        db.execute("""
            INSERT INTO review_notes (
                search_id, source, listing_id,
                seller_name, contact_status,
                note_text, updated_utc
            )
            VALUES (?, 'olx', ?, ?, ?, ?, ?)
            ON CONFLICT(search_id, source, listing_id)
            DO UPDATE SET
                seller_name=excluded.seller_name,
                contact_status=excluded.contact_status,
                note_text=excluded.note_text,
                updated_utc=excluded.updated_utc
        """, (sid, lid, seller, status, note, stamp))

        db.execute("""
            INSERT INTO review_note_history (
                search_id, source, listing_id,
                seller_name, contact_status,
                note_text, event_kind, created_utc
            )
            VALUES (?, 'olx', ?, ?, ?, ?, 'update', ?)
        """, (sid, lid, seller, status, note, stamp))

    return True


def attach_history(report, path=DB):
    result = dict(report)
    path = Path(path)

    with sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=15
    ) as db:
        db.row_factory = sqlite3.Row

        for group in ("items", "handled"):
            enriched = []

            for original in report.get(group, []):
                item = dict(original)

                rows = db.execute("""
                    SELECT seller_name, contact_status,
                           note_text, event_kind, created_utc
                    FROM review_note_history
                    WHERE search_id=? AND source='olx'
                      AND listing_id=?
                    ORDER BY id DESC
                    LIMIT 20
                """, (
                    item["search_id"],
                    item["listing_id"]
                )).fetchall()

                item["history"] = [
                    dict(row) for row in rows
                ]

                enriched.append(item)

            result[group] = enriched

    return result
