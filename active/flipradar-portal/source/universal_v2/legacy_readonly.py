"""Odczyt legacy offer_snapshots.db bez zapisu i skanowania."""

import sqlite3
from pathlib import Path


def recent(path, limit=20, before_id=None, search=''):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit 1..100')

    if before_id is not None and (
        type(before_id) is not int
        or before_id < 1
    ):
        raise ValueError('bledny kursor')

    if not isinstance(search, str) or len(search) > 120:
        raise ValueError('bledne wyszukiwanie')

    dbfile = Path(path).resolve(strict=True)

    if (
        not dbfile.is_file()
        or dbfile.name != 'offer_snapshots.db'
    ):
        raise ValueError(
            'wymagana baza offer_snapshots.db'
        )

    with sqlite3.connect(
        dbfile.as_uri() + '?mode=ro',
        uri=True,
        timeout=5
    ) as db:

        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')

        escaped = (
            search
            .replace('\\', '\\\\')
            .replace('%', '\\%')
            .replace('_', '\\_')
        )

        rows = db.execute('''
            WITH newest AS (
                SELECT offer_key, MAX(id) AS max_id
                FROM snapshots
                GROUP BY offer_key
            )
            SELECT
                s.id,
                s.offer_key,
                s.title,
                s.url,
                s.created_at
            FROM snapshots s
            JOIN newest n
                ON s.id = n.max_id
            WHERE (? IS NULL OR s.id < ?)
              AND s.title LIKE ? ESCAPE '\\'
            ORDER BY s.id DESC
            LIMIT ?
        ''', (
            before_id,
            before_id,
            '%' + escaped + '%',
            limit
        )).fetchall()

    return [dict(r) for r in rows]
