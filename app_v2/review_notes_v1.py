import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from .saved_searches_v1 import DB

STATUSES = {
    "none", "messaged", "replied",
    "meeting", "closed"
}


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
            CREATE TABLE IF NOT EXISTS review_notes (
                search_id INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'olx',
                listing_id TEXT NOT NULL,
                seller_name TEXT NOT NULL DEFAULT '',
                contact_status TEXT NOT NULL DEFAULT 'none',
                note_text TEXT NOT NULL DEFAULT '',
                updated_utc TEXT NOT NULL,
                PRIMARY KEY(search_id,source,listing_id)
            )
        """)


def save_notes(
    search_id, listing_id, seller_name,
    contact_status, note_text, path=DB
):
    search_id = int(search_id)
    listing_id = str(listing_id or "").strip()
    seller_name = str(seller_name or "").strip()
    contact_status = str(contact_status or "none").strip()
    note_text = str(note_text or "").strip()

    if search_id < 1 or not 1 <= len(listing_id) <= 120:
        raise ValueError("Nieprawidlowa oferta")

    if contact_status not in STATUSES:
        raise ValueError("Nieznany status kontaktu")

    if len(seller_name) > 120 or len(note_text) > 3000:
        raise ValueError("Zbyt dluga notatka")

    with connect(path) as db:
        exists = db.execute("""
            SELECT 1 FROM saved_search_matches
            WHERE search_id=? AND source='olx'
              AND listing_id=?
              AND match_status IN ('MATCH','REVIEW')
        """, (search_id, listing_id)).fetchone()

        if not exists:
            raise ValueError("Nie znaleziono oferty")

        db.execute("""
            INSERT INTO review_notes
            (search_id,source,listing_id,
             seller_name,contact_status,
             note_text,updated_utc)
            VALUES (?, 'olx', ?, ?, ?, ?, ?)
            ON CONFLICT(search_id,source,listing_id)
            DO UPDATE SET
              seller_name=excluded.seller_name,
              contact_status=excluded.contact_status,
              note_text=excluded.note_text,
              updated_utc=excluded.updated_utc
        """, (
            search_id, listing_id, seller_name,
            contact_status, note_text,
            datetime.now(timezone.utc).isoformat()
        ))


def attach_notes(report, path=DB):
    result = dict(report)

    with connect(path, readonly=True) as db:
        for group in ("items", "handled"):
            enriched = []

            for original in report.get(group, []):
                item = dict(original)

                row = db.execute("""
                    SELECT seller_name,contact_status,
                           note_text,updated_utc
                    FROM review_notes
                    WHERE search_id=?
                      AND source='olx'
                      AND listing_id=?
                """, (
                    item["search_id"],
                    item["listing_id"]
                )).fetchone()

                item["seller_name"] = row[0] if row else ""
                item["contact_status"] = row[1] if row else "none"
                item["note_text"] = row[2] if row else ""
                item["note_updated_utc"] = row[3] if row else None

                enriched.append(item)

            result[group] = enriched

    return result
