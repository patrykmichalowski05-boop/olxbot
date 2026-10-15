import json
import sqlite3
from pathlib import Path

DB = Path('/opt/olx-bot/offer_snapshots.db')


def get_radar_items(limit=100):
    limit = max(1, min(int(limit), 200))
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("""
            SELECT id, offer_key, title, url, price,
                   valuation_json, action_json, created_at
            FROM snapshots
            WHERE id IN (
                SELECT MAX(id) FROM snapshots GROUP BY offer_key
            )
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [normalize(dict(row)) for row in rows]

def normalize(row):
    valuation = json.loads(row['valuation_json'] or '{}')
    action = json.loads(row['action_json'] or '{}')
    confidence = str(valuation.get('confidence') or 'BRAK')
    return {
        'id': row['id'],
        'offer_key': row['offer_key'],
        'title': row['title'],
        'url': row['url'],
        'price_pln': row['price'],
        'profit_pln': valuation.get('profit'),
        'quick_sale_pln': valuation.get('quick_sale'),
        'decision': action.get('action', 'UNKNOWN'),
        'reason': action.get('reason', ''),
        'confidence': confidence,
        'requires_review': confidence.upper() in (
            'LOW', 'VERY_LOW', 'NISKI', 'BARDZO NISKI'
        ),
        'analyzed_at': row['created_at'],
    }


if __name__ == '__main__':
    print(json.dumps(
        {'items': get_radar_items()},
        ensure_ascii=False, indent=2
    ))
