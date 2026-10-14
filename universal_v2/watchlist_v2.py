"""Watchlista z oddzielnymi danymi uzytkownikow."""

import sqlite3

from pathlib import Path
from .model import utc


class Watchlist:

    def __init__(self, path):
        self.path = Path(path).resolve()

        prod = Path('/opt/olx-bot')

        if self.path == prod or prod in self.path.parents:
            raise ValueError(
                'Baza produkcyjna zabroniona'
            )

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with sqlite3.connect(self.path) as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS watchlist(
                    id INTEGER PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    listing_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    state TEXT NOT NULL,
                    updated TEXT NOT NULL,
                    UNIQUE(user_id,listing_key)
                )
            ''')

    def put(self, user_id, listing_key, label):
        values = (user_id, listing_key, label)

        if not all(
            isinstance(x, str)
            and 1 <= len(x.strip()) <= 240
            for x in values
        ):
            raise ValueError('Bledny wpis')

        with sqlite3.connect(self.path) as db:
            db.execute('''
                INSERT INTO watchlist(
                    user_id,
                    listing_key,
                    label,
                    state,
                    updated
                )
                VALUES(?,?,?,'WATCH',?)
                ON CONFLICT(user_id,listing_key)
                DO UPDATE SET
                    label=excluded.label,
                    state='WATCH',
                    updated=excluded.updated
            ''', (
                user_id,
                listing_key,
                label,
                utc()
            ))

    def close(self, user_id, listing_key):
        with sqlite3.connect(self.path) as db:
            result = db.execute('''
                UPDATE watchlist
                SET
                    state='CLOSED',
                    updated=?
                WHERE user_id=?
                  AND listing_key=?
                  AND state='WATCH'
            ''', (
                utc(),
                user_id,
                listing_key
            ))

            return result.rowcount == 1

    def get(self, user_id, limit=30):
        if (
            type(limit) is not int
            or not 1 <= limit <= 100
        ):
            raise ValueError('Limit 1-100')

        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row

            rows = db.execute('''
                SELECT
                    listing_key,
                    label,
                    updated
                FROM watchlist
                WHERE user_id=?
                  AND state='WATCH'
                ORDER BY id DESC
                LIMIT ?
            ''', (
                user_id,
                limit
            )).fetchall()

            return [dict(x) for x in rows]
