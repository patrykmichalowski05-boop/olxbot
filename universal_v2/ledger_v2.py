"""Transakcyjny rejestr zakupow, kosztow i sprzedazy."""

import sqlite3

from pathlib import Path
from contextlib import contextmanager

from .model import assert_minor, utc


class Ledger:

    def __init__(self, path):
        self.path = Path(path).resolve()

        prod = Path('/opt/olx-bot')

        if self.path == prod or prod in self.path.parents:
            raise ValueError(
                'Baza produkcyjna zabroniona'
            )

    def connect(self):
        db = sqlite3.connect(
            self.path,
            timeout=15,
            isolation_level=None
        )

        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def connection(self):
        db = self.connect()

        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    UNIQUE(user_id,item_key)
                );

                CREATE TABLE IF NOT EXISTS ledger_events (
                    id INTEGER PRIMARY KEY,
                    item_id INTEGER NOT NULL REFERENCES items(id),
                    user_id TEXT NOT NULL,
                    request_key TEXT NOT NULL,
                    kind TEXT NOT NULL
                      CHECK(kind IN ('PURCHASE','COST','SALE')),
                    amount_minor INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    UNIQUE(user_id,request_key)
                );
            ''')

    def record(
        self, user_id, item_key,
        request_key, kind, amount_minor
    ):
        if not all(
            isinstance(x, str) and x.strip()
            for x in (user_id, item_key, request_key)
        ):
            raise ValueError('Brak identyfikatora')

        if kind not in {'PURCHASE', 'COST', 'SALE'}:
            raise ValueError('Zly rodzaj operacji')

        assert_minor(amount_minor)

        if kind != 'COST' and amount_minor == 0:
            raise ValueError('Kwota musi byc dodatnia')

        with self.connection() as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')

            old = db.execute('''
                SELECT
                    e.id,
                    e.kind,
                    e.amount_minor,
                    i.item_key
                FROM ledger_events e
                JOIN items i ON i.id=e.item_id
                WHERE e.user_id=?
                  AND e.request_key=?
            ''', (
                user_id, request_key
            )).fetchone()

            if old:
                same = (
                    old['kind'],
                    old['amount_minor'],
                    old['item_key']
                ) == (
                    kind,
                    amount_minor,
                    item_key
                )

                if not same:
                    raise ValueError(
                        'Klucz idempotencji zajety'
                    )

                return old['id'], False

            row = db.execute('''
                SELECT id,status
                FROM items
                WHERE user_id=? AND item_key=?
            ''', (
                user_id, item_key
            )).fetchone()

            if row is None:
                if kind != 'PURCHASE':
                    raise ValueError(
                        'Najpierw zarejestruj zakup'
                    )

                cur = db.execute('''
                    INSERT INTO items(
                        user_id,item_key,status
                    )
                    VALUES(?,?,'BOUGHT')
                ''', (
                    user_id, item_key
                ))

                item_id = cur.lastrowid
                status = 'BOUGHT'

            else:
                item_id = row['id']
                status = row['status']

                if kind == 'PURCHASE':
                    raise ValueError(
                        'Zakup juz zarejestrowany'
                    )

                if kind == 'SALE' and status != 'BOUGHT':
                    raise ValueError(
                        'Przedmiot juz sprzedany'
                    )

                if (
                    kind == 'COST'
                    and status not in ('BOUGHT', 'SOLD')
                ):
                    raise ValueError('Zly status')

            cur = db.execute('''
                INSERT INTO ledger_events(
                    item_id,
                    user_id,
                    request_key,
                    kind,
                    amount_minor,
                    ts
                )
                VALUES(?,?,?,?,?,?)
            ''', (
                item_id,
                user_id,
                request_key,
                kind,
                amount_minor,
                utc()
            ))

            if kind == 'SALE':
                db.execute('''
                    UPDATE items
                    SET status='SOLD'
                    WHERE id=?
                ''', (item_id,))

            return cur.lastrowid, True

    def totals(self, user_id, item_key):
        with self.connection() as db:
            row = db.execute('''
                SELECT id,status
                FROM items
                WHERE user_id=?
                  AND item_key=?
            ''', (
                user_id, item_key
            )).fetchone()

            if row is None:
                return None

            events = db.execute('''
                SELECT kind,SUM(amount_minor)
                FROM ledger_events
                WHERE item_id=?
                  AND user_id=?
                GROUP BY kind
            ''', (
                row['id'], user_id
            )).fetchall()

            amounts = {
                kind: value
                for kind, value in events
            }

            buy = amounts.get('PURCHASE', 0)
            cost = amounts.get('COST', 0)
            sale = amounts.get('SALE', 0)

            return {
                'status': row['status'],
                'purchase_minor': buy,
                'cost_minor': cost,
                'sale_minor': sale,
                'realized_profit_minor': (
                    sale - buy - cost
                    if row['status'] == 'SOLD'
                    else None
                )
            }
