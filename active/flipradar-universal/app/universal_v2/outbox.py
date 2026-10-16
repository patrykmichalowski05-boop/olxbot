import json
import sqlite3

from pathlib import Path

from .model import utc


class Outbox:

    def __init__(self, path):
        self.path = Path(
            path
        ).resolve()

        if (
            self.path == Path('/opt/olx-bot')
            or Path('/opt/olx-bot')
            in self.path.parents
        ):
            raise ValueError(
                'Baza produkcyjna zabroniona'
            )

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sqlite3.connect(
            self.path
        ) as d:
            d.execute('''
                CREATE TABLE IF NOT EXISTS
                notifications (
                    id INTEGER PRIMARY KEY,
                    item_key TEXT UNIQUE NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created TEXT NOT NULL
                )
            ''')

    def enqueue(
        self,
        key,
        payload,
    ):
        with sqlite3.connect(
            self.path,
            timeout=15,
        ) as d:
            d.execute(
                'BEGIN IMMEDIATE'
            )

            q = d.execute('''
                INSERT OR IGNORE
                INTO notifications(
                    item_key,
                    payload,
                    status,
                    created
                )
                VALUES(?,?,?,?)
            ''', (
                key,
                json.dumps(
                    payload,
                    sort_keys=True,
                ),
                'PENDING',
                utc(),
            ))

            return bool(q.rowcount)

    def pending(self):
        with sqlite3.connect(
            self.path
        ) as d:
            return d.execute('''
                SELECT COUNT(*)
                FROM notifications
                WHERE status='PENDING'
            ''').fetchone()[0]
