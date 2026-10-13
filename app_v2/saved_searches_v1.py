import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path('/opt/olx-bot-ui-dev/data/flip_radar_dev.sqlite3')

CATEGORIES = {
    'pc', 'laptop', 'gpu', 'cpu',
    'ram', 'motherboard', 'ssd', 'other'
}


def connection(path=DB, readonly=False):
    path = Path(path)

    if path.is_symlink() or not path.is_file():
        raise RuntimeError('Nieprawidlowa baza danych')

    uri = path.resolve().as_uri() + '?mode=ro'

    db = sqlite3.connect(
        uri if readonly else path,
        uri=readonly,
        timeout=15
    )

    db.row_factory = sqlite3.Row
    return db


def initialize(path=DB):
    with connection(path) as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_json TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                archived INTEGER NOT NULL DEFAULT 0,
                updated_utc TEXT NOT NULL
            )
        ''')


def price(value, label):
    value = str(value or '').strip()

    if value in ('', '0'):
        return None

    if not value.isdecimal() or int(value) > 10000000:
        raise ValueError(
            'Nieprawidlowa wartosc: ' + label
        )

    return int(value)


def validate(form):
    text = lambda key: str(form.get(key) or '').strip()

    query = text('query_text')
    name = text('name') or query

    if not 2 <= len(query) <= 150:
        raise ValueError('Fraza musi miec 2-150 znakow')

    if not 2 <= len(name) <= 100:
        raise ValueError('Nazwa musi miec 2-100 znakow')

    fields = {
        'category': CATEGORIES,
        'purpose': {'cheap', 'flip'},
        'source': {'both', 'olx', 'facebook'},
        'priority': {'normal', 'high'}
    }

    for key, choices in fields.items():
        if text(key) not in choices:
            raise ValueError('Nieznany parametr: ' + key)

    low = price(text('min_price_zl'), 'cena minimalna')
    high = price(text('max_price_zl'), 'cena maksymalna')

    if low and high and low > high:
        raise ValueError(
            'Cena minimalna przekracza maksymalna'
        )

    try:
        profit = int(text('min_profit_zl'))
        roi = float(
            text('min_roi_pct').replace(',', '.')
        )
    except ValueError:
        raise ValueError('Nieprawidlowy zysk lub ROI')

    if not 0 <= profit <= 1000000:
        raise ValueError('Zysk poza zakresem')

    if not math.isfinite(roi) or not 0 <= roi <= 300:
        raise ValueError('ROI poza zakresem')

    extras = {
        k: text(k)
        for k in ('brand', 'socket', 'notes')
    }

    if any(len(v) > 300 for v in extras.values()):
        raise ValueError('Zbyt dlugi parametr')

    extras['capacity_gb'] = price(
        text('capacity_gb'),
        'pojemnosc GB'
    )

    return dict(
        name=name,
        query_text=query,
        min_price_zl=low,
        max_price_zl=high,
        min_profit_zl=profit,
        min_roi_pct=roi,
        **{k: text(k) for k in fields},
        **extras
    )


def unpack(row):
    if not row:
        return None

    return dict(
        id=row['id'],
        enabled=bool(row['enabled']),
        **json.loads(row['config_json'])
    )


def all_searches(path=DB):
    with connection(path, True) as db:
        rows = db.execute('''
            SELECT * FROM saved_searches
            WHERE archived=0
            ORDER BY enabled DESC, id DESC
        ''').fetchall()

    return [unpack(r) for r in rows]


def one_search(search_id, path=DB):
    with connection(path, True) as db:
        row = db.execute('''
            SELECT * FROM saved_searches
            WHERE id=? AND archived=0
        ''', (search_id,)).fetchone()

    return unpack(row)


def save_search(form, search_id=None, path=DB):
    config = json.dumps(
        validate(form),
        ensure_ascii=False
    )

    stamp = datetime.now(timezone.utc).isoformat()

    with connection(path) as db:
        if search_id is None:
            cur = db.execute('''
                INSERT INTO saved_searches
                (config_json, updated_utc)
                VALUES (?, ?)
            ''', (config, stamp))

        else:
            cur = db.execute('''
                UPDATE saved_searches
                SET config_json=?, updated_utc=?
                WHERE id=? AND archived=0
            ''', (config, stamp, search_id))

            if cur.rowcount != 1:
                raise ValueError(
                    'Nie znaleziono wyszukiwania'
                )

        return (
            cur.lastrowid
            if search_id is None
            else search_id
        )


def change_status(search_id, action, path=DB):
    clauses = {
        'pause': 'enabled=0',
        'resume': 'enabled=1',
        'archive': 'archived=1, enabled=0'
    }

    if action not in clauses:
        raise ValueError('Nieznana operacja')

    with connection(path) as db:
        cur = db.execute(
            'UPDATE saved_searches SET '
            + clauses[action]
            + ' WHERE id=? AND archived=0',
            (search_id,)
        )

        if cur.rowcount != 1:
            raise ValueError(
                'Nie znaleziono wyszukiwania'
            )
