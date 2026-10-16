import json
import secrets
import sqlite3
import time

from pathlib import Path


class Dispatch:

    def __init__(self, path):
        self.path = Path(path).resolve()
        prod = Path('/opt/olx-bot')

        if (
            self.path == prod
            or prod in self.path.parents
        ):
            raise ValueError(
                'Zabroniona baza produkcyjna'
            )

    def connect(self):
        db = sqlite3.connect(
            self.path,
            timeout=15
        )
        db.row_factory = sqlite3.Row
        return db

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.connect() as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS dispatch (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    unique_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    token TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    due INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id,unique_key)
                )
            ''')

    def put(self, user, key, payload):
        if not user or not key:
            raise ValueError(
                'Brak identyfikatora'
            )

        raw = json.dumps(
            payload,
            allow_nan=False,
            sort_keys=True
        )

        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')

            old = db.execute('''
                SELECT payload
                FROM dispatch
                WHERE user_id=? AND unique_key=?
            ''', (user, key)).fetchone()

            if old is not None:
                if old['payload'] != raw:
                    raise ValueError(
                        'Konflikt klucza idempotencji'
                    )
                return False

            db.execute('''
                INSERT INTO dispatch (
                    user_id,
                    unique_key,
                    payload
                )
                VALUES(?,?,?)
            ''', (
                user,
                key,
                raw
            ))

            return True

    def claim(self, now=None):
        stamp = int(
            time.time() if now is None else now
        )

        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')

            db.execute('''
                UPDATE dispatch
                SET state='FAILED', token=NULL
                WHERE state='CLAIMED'
                  AND due<?
                  AND attempts>=4
            ''', (stamp,))

            row = db.execute('''
                SELECT *
                FROM dispatch
                WHERE (
                    (
                        state IN ('PENDING','RETRY')
                        AND due<=?
                    )
                    OR (
                        state='CLAIMED'
                        AND due<?
                    )
                )
                AND attempts<4
                ORDER BY id
                LIMIT 1
            ''', (stamp, stamp)).fetchone()

            if row is None:
                return None

            token = secrets.token_urlsafe(24)

            db.execute('''
                UPDATE dispatch
                SET
                    state='CLAIMED',
                    token=?,
                    due=?,
                    attempts=attempts+1
                WHERE id=?
            ''', (
                token,
                stamp + 60,
                row['id']
            ))

            return {
                'id': row['id'],
                'token': token,
                'user_id': row['user_id'],
                'payload': json.loads(
                    row['payload']
                ),
                'attempt': row['attempts'] + 1
            }

    def finish(self, job, success, now=None):
        stamp = int(
            time.time() if now is None else now
        )

        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')

            row = db.execute('''
                SELECT *
                FROM dispatch
                WHERE id=?
                  AND state='CLAIMED'
                  AND token=?
            ''', (
                job['id'],
                job['token']
            )).fetchone()

            if row is None:
                raise ValueError(
                    'Dzierzawa wygasla lub token zly'
                )

            if success:
                state, due = 'DONE', 0

            elif row['attempts'] >= 4:
                state, due = 'FAILED', 0

            else:
                state = 'RETRY'
                due = stamp + min(
                    3600,
                    30 * 2 ** row['attempts']
                )

            db.execute('''
                UPDATE dispatch
                SET
                    state=?,
                    due=?,
                    token=NULL
                WHERE id=?
            ''', (
                state,
                due,
                row['id']
            ))

            return state
