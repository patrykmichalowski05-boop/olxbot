import sqlite3
from pathlib import Path

from .saved_searches_v1 import DB

TABLE = "saved_search_price_history"

VALID = """
NEW.source='olx'
AND NEW.match_status IN ('MATCH','REVIEW')
AND CAST(NEW.asking_price_zl AS INTEGER) BETWEEN 1 AND 2000000
AND TRIM(CAST(NEW.asking_price_zl AS TEXT)) =
    CAST(CAST(NEW.asking_price_zl AS INTEGER) AS TEXT)
"""

PREVIOUS = """
(SELECT new_price_zl
 FROM saved_search_price_history
 WHERE search_id=NEW.search_id
   AND source=NEW.source
   AND listing_id=NEW.listing_id
 ORDER BY id DESC LIMIT 1)
"""


def initialize(path=DB):
    path = Path(path)

    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Nie znaleziono bazy SQLite")

    with sqlite3.connect(path, timeout=20) as db:
        db.execute("BEGIN IMMEDIATE")

        db.execute("""
            CREATE TABLE IF NOT EXISTS saved_search_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                old_price_zl INTEGER,
                new_price_zl INTEGER NOT NULL,
                event_kind TEXT NOT NULL,
                observed_utc TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_prices_offer
            ON saved_search_price_history
            (search_id, source, listing_id, id)
        """)

        # Stan obecny jest punktem odniesienia,
        # a nie dowodem historycznej sprzedazy.
        db.execute("""
            INSERT INTO saved_search_price_history
            (search_id, source, listing_id, old_price_zl,
             new_price_zl, event_kind, observed_utc)
            SELECT
                m.search_id, m.source, m.listing_id, NULL,
                CAST(m.asking_price_zl AS INTEGER),
                'baseline',
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            FROM saved_search_matches m
            WHERE m.source='olx'
              AND m.match_status IN ('MATCH','REVIEW')
              AND CAST(m.asking_price_zl AS INTEGER)
                  BETWEEN 1 AND 2000000
              AND TRIM(CAST(m.asking_price_zl AS TEXT)) =
                  CAST(CAST(m.asking_price_zl AS INTEGER) AS TEXT)
              AND NOT EXISTS (
                  SELECT 1 FROM saved_search_price_history h
                  WHERE h.search_id=m.search_id
                    AND h.source=m.source
                    AND h.listing_id=m.listing_id
              )
        """)

        for action in ("INSERT", "UPDATE"):
            trigger = "trg_saved_price_" + action.lower()

            db.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {trigger}
                AFTER {action} ON saved_search_matches
                WHEN {VALID}
                BEGIN
                    INSERT INTO saved_search_price_history
                    (search_id,source,listing_id,old_price_zl,
                     new_price_zl,event_kind,observed_utc)
                    SELECT
                        NEW.search_id,
                        NEW.source,
                        NEW.listing_id,
                        {PREVIOUS},
                        CAST(NEW.asking_price_zl AS INTEGER),
                        CASE WHEN {PREVIOUS} IS NULL
                             THEN 'first_seen'
                             ELSE 'change' END,
                        strftime('%Y-%m-%dT%H:%M:%fZ','now')
                    WHERE {PREVIOUS} IS NOT
                        CAST(NEW.asking_price_zl AS INTEGER);
                END
            """)


def recent_drops(path=DB, limit=20):
    path = Path(path)

    with sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=15
    ) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT h.*, m.title, m.url, m.match_status
            FROM saved_search_price_history h
            JOIN saved_search_matches m
              ON m.search_id=h.search_id
             AND m.source=h.source
             AND m.listing_id=h.listing_id
            WHERE h.event_kind='change'
              AND h.old_price_zl > h.new_price_zl
              AND m.match_status IN ('MATCH','REVIEW')
            ORDER BY h.id DESC
            LIMIT ?
        """, (max(1, min(int(limit), 100)),)).fetchall()

        return [dict(row) for row in rows]
