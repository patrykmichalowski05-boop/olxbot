import sqlite3
from datetime import datetime, timezone, timedelta
from .saved_searches_v1 import DB


def get_search_stats():
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).isoformat()

    uri = DB.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True, timeout=10) as db:
        db.row_factory = sqlite3.Row

        rows = db.execute("""
            SELECT
                s.id,
                r.status,
                r.last_attempt_utc,
                r.scanned_cards,
                r.saved_matches,
                r.message,

                SUM(
                    CASE WHEN m.match_status='MATCH'
                    THEN 1 ELSE 0 END
                ) AS match_count,

                SUM(
                    CASE WHEN m.match_status='REVIEW'
                    THEN 1 ELSE 0 END
                ) AS review_count,

                SUM(
                    CASE WHEN m.match_status='REJECT'
                    THEN 1 ELSE 0 END
                ) AS rejected_count,

                SUM(
                    CASE
                    WHEN m.match_status IN ('MATCH','REVIEW')
                         AND m.first_seen_utc >= ?
                    THEN 1 ELSE 0 END
                ) AS new_24h_count

            FROM saved_searches s
            LEFT JOIN saved_search_runs r
                ON r.search_id = s.id
            LEFT JOIN saved_search_matches m
                ON m.search_id = s.id

            WHERE s.archived=0

            GROUP BY s.id
        """, (cutoff,)).fetchall()

    return {
        row["id"]: dict(row)
        for row in rows
    }
