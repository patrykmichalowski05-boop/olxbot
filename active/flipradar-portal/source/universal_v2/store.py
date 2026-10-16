import hashlib
import json
import sqlite3

from pathlib import Path
from dataclasses import asdict
from contextlib import contextmanager

from .model import Listing, utc


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(',', ':'),
        allow_nan=False,
    )


class Store:

    def __init__(self, path):
        self.path = Path(
            path
        ).expanduser().resolve()

        if (
            self.path == Path('/opt/olx-bot')
            or Path('/opt/olx-bot')
            in self.path.parents
        ):
            raise ValueError(
                'Baza produkcyjna zabroniona'
            )

    @contextmanager
    def tx(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        db = sqlite3.connect(
            self.path,
            timeout=15,
            isolation_level=None,
        )

        db.row_factory = sqlite3.Row

        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()

        except BaseException:
            db.rollback()
            raise

        finally:
            db.close()

    def init(self):
        with self.tx() as d:
            d.execute('''
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY,
                    source TEXT,
                    ext TEXT,
                    digest TEXT,
                    payload TEXT,
                    ts TEXT,
                    UNIQUE(source, ext, digest)
                )
            ''')

            d.execute('''
                CREATE TABLE IF NOT EXISTS valuations (
                    id INTEGER PRIMARY KEY,
                    observation_id INTEGER,
                    engine TEXT,
                    profile TEXT,
                    market TEXT,
                    result TEXT,
                    ts TEXT,
                    UNIQUE(
                        observation_id,
                        engine,
                        profile,
                        market
                    )
                )
            ''')

    def observe(self, row: Listing):
        payload = asdict(row)

        payload['price_kind'] = (
            row.price_kind.value
        )

        data = {
            k: v
            for k, v in payload.items()
            if k != 'observed_at'
        }

        digest = hashlib.sha256(
            canonical(data).encode()
        ).hexdigest()

        with self.tx() as d:
            old = d.execute('''
                SELECT id
                FROM observations
                WHERE source=?
                AND ext=?
                AND digest=?
            ''', (
                row.source,
                row.external_id,
                digest,
            )).fetchone()

            if old:
                return old['id'], False

            n = d.execute('''
                INSERT INTO observations(
                    source,
                    ext,
                    digest,
                    payload,
                    ts
                )
                VALUES(?,?,?,?,?)
            ''', (
                row.source,
                row.external_id,
                digest,
                canonical(payload),
                utc(),
            ))

            return n.lastrowid, True

    def valuation(
        self,
        obs,
        engine,
        profile,
        market,
        result,
    ):
        raw = canonical(result)

        with self.tx() as d:
            old = d.execute('''
                SELECT id, result
                FROM valuations
                WHERE observation_id=?
                AND engine=?
                AND profile=?
                AND market=?
            ''', (
                obs,
                engine,
                profile,
                market,
            )).fetchone()

            if old:
                if old['result'] != raw:
                    raise ValueError(
                        'Wersja wyceny koliduje z poprzednią'
                    )

                return old['id'], False

            n = d.execute('''
                INSERT INTO valuations(
                    observation_id,
                    engine,
                    profile,
                    market,
                    result,
                    ts
                )
                VALUES(?,?,?,?,?,?)
            ''', (
                obs,
                engine,
                profile,
                market,
                raw,
                utc(),
            ))

            return n.lastrowid, True
