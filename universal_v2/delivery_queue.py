"""Kolejka testowa bez Telegrama i push."""

import json
import sqlite3
import time

from pathlib import Path


class DeliveryQueue:

    def __init__(self, path):
        self.path = Path(path).resolve()

        if Path('/opt/olx-bot') in self.path.parents:
            raise ValueError(
                'zabroniona baza produkcyjna'
            )

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with sqlite3.connect(self.path) as d:
            d.execute('''
                CREATE TABLE IF NOT EXISTS jobs(
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    lease INTEGER NOT NULL DEFAULT 0,
                    tries INTEGER NOT NULL DEFAULT 0
                )
            ''')

    def put(self, key, payload):
        if not isinstance(key, str) or not key:
            raise ValueError('brak klucza')

        with sqlite3.connect(
            self.path,
            timeout=10
        ) as d:
            result = d.execute('''
                INSERT OR IGNORE INTO jobs(
                    key,
                    payload
                )
                VALUES(?,?)
            ''', (
                key,
                json.dumps(payload)
            ))

            return bool(result.rowcount)

    def claim(self):
        now = int(time.time())

        with sqlite3.connect(
            self.path,
            timeout=10
        ) as d:

            d.execute('BEGIN IMMEDIATE')

            row = d.execute('''
                SELECT id,payload,tries
                FROM jobs
                WHERE (
                    state='PENDING'
                    OR (
                        state='CLAIMED'
                        AND lease < ?
                    )
                )
                AND tries < 3
                ORDER BY id
                LIMIT 1
            ''', (now,)).fetchone()

            if row is None:
                return None

            d.execute('''
                UPDATE jobs
                SET
                    state='CLAIMED',
                    lease=?,
                    tries=tries+1
                WHERE id=?
            ''', (
                now + 60,
                row[0]
            ))

            return {
                'id': row[0],
                'payload': json.loads(row[1]),
                'attempt': row[2] + 1
            }

    def ack(self, job_id):
        with sqlite3.connect(self.path) as d:
            result = d.execute('''
                UPDATE jobs
                SET state='DONE'
                WHERE id=?
                AND state='CLAIMED'
            ''', (job_id,))

            return bool(result.rowcount)
