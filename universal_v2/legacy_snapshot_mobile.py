"""Historia skanera OLX: tylko odczyt."""
import json
import sqlite3
from pathlib import Path

DB = Path('/opt/olx-bot/offer_snapshots.db')


def _as_item(row):
    valuation = json.loads(row['valuation_json'] or '{}')
    action = json.loads(row['action_json'] or '{}')
    if not isinstance(valuation, dict) or not isinstance(action, dict):
        raise ValueError('Invalid snapshot JSON')

    valuation.setdefault('category', 'ELECTRONICS')
    title = row['title'] or ''

    return {
        'snapshot_id': row['id'],
        'offer_key': row['offer_key'],
        'title': title,
        'url': row['url'],
        'platform': 'FACEBOOK' if title.startswith(
            '[FB Marketplace]') else 'OLX',
        'price_minor': int(round(float(row['price']) * 100))
            if row['price'] is not None else None,
        'observed_at': row['created_at'],
        'decision': action.get('action', 'UNKNOWN'),
        'valuation': valuation,
        'source_status': 'HISTORICAL',
    }


def page(limit=20, before_id=None, q='', db_path=DB):
    if not 1 <= limit <= 100 or len(q) > 120:
        raise ValueError('Invalid radar query')

    path = Path(db_path).resolve(strict=True)
    if path.name != 'offer_snapshots.db':
        raise ValueError('Unexpected database')

    with sqlite3.connect(path.as_uri() + '?mode=ro',
                         uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        rows = db.execute("""
            WITH newest AS (
                SELECT MAX(id) AS id FROM snapshots GROUP BY offer_key
            )
            SELECT s.* FROM snapshots s JOIN newest n ON s.id=n.id
            WHERE (? IS NULL OR s.id < ?)
              AND (instr(lower(coalesce(s.title,'')),lower(?))>0
                OR instr(lower(s.offer_key),lower(?))>0)
            ORDER BY s.id DESC LIMIT ?
        """, (before_id, before_id, q, q, limit+1)).fetchall()
    items = [_as_item(row) for row in rows[:limit]]

    return {
        'items': items,
        'next_before_id': items[-1]['snapshot_id']
            if len(rows) > limit else None,
    }


def get_snapshot(snapshot_id, db_path=DB):
    if type(snapshot_id) is not int or snapshot_id <= 0:
        raise ValueError('Invalid snapshot ID')

    path = Path(db_path).resolve(strict=True)
    if path.name != 'offer_snapshots.db':
        raise ValueError('Unexpected database')

    with sqlite3.connect(
        path.as_uri() + '?mode=ro', uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        row = db.execute(
            'SELECT * FROM snapshots WHERE id=?',
            (snapshot_id,)
        ).fetchone()

    return _as_item(row) if row is not None else None
