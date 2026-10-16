"""Radar testowy na izolowanej bazie SQLite."""

import sqlite3
from pathlib import Path


def radar(
    path,
    user_id,
    q='',
    limit=20,
    cursor=None
):
    if (
        not isinstance(user_id, str)
        or not user_id.strip()
    ):
        raise ValueError('brak uzytkownika')

    if (
        type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise ValueError('limit')

    if (
        not isinstance(q, str)
        or len(q) > 120
    ):
        raise ValueError('fraza')

    if cursor is not None and (
        type(cursor) is not int
        or cursor <= 0
    ):
        raise ValueError('kursor')

    p = Path(path).resolve(strict=True)

    escaped = (
        q
        .replace('\\', '\\\\')
        .replace('%', '\\%')
        .replace('_', '\\_')
    )

    with sqlite3.connect(
        p.as_uri() + '?mode=ro',
        uri=True
    ) as d:

        d.row_factory = sqlite3.Row
        d.execute('PRAGMA query_only=ON')

        rows = d.execute('''
            WITH latest AS (
                SELECT
                    source,
                    ext,
                    MAX(id) AS obs_id
                FROM observations
                GROUP BY source,ext
            )
            SELECT
                o.id,
                o.source,
                o.ext,
                json_extract(
                    o.payload,
                    '$.title'
                ) AS title,
                o.payload AS payload,
                v.result AS result
            FROM latest x
            JOIN observations o
                ON o.id=x.obs_id
            JOIN valuations v
                ON v.observation_id=o.id
            WHERE v.id=(
                SELECT MAX(w.id)
                FROM valuations w
                WHERE w.observation_id=o.id
                  AND w.profile=?
            )
              AND (? IS NULL OR o.id<?)
              AND json_extract(
                    o.payload,
                    '$.title'
                  ) LIKE ? ESCAPE '\\'
            ORDER BY o.id DESC
            LIMIT ?
        ''', (
            'profile-' + user_id,
            cursor,
            cursor,
            '%' + escaped + '%',
            limit
        )).fetchall()

    return [dict(r) for r in rows]
