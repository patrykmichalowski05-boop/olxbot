import hashlib
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path


def canonical(data):
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(data):
    return hashlib.sha256(
        canonical(data).encode("utf-8")
    ).hexdigest()


class ObservationStore:

    def __init__(self, path):
        self.path = Path(path).resolve()

    def connect(self):
        db = sqlite3.connect(
            self.path,
            timeout=15,
            isolation_level=None,
        )

        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")

        return db

    def init_db(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS
                listing_observations (
                    id INTEGER PRIMARY KEY,
                    listing_key TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(listing_key,content_hash)
                );

                CREATE TABLE IF NOT EXISTS
                valuation_runs (
                    id INTEGER PRIMARY KEY,
                    observation_id INTEGER NOT NULL
                        REFERENCES listing_observations(id),
                    engine_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    market_snapshot_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(
                        observation_id,
                        engine_version,
                        policy_version,
                        market_snapshot_id
                    )
                );
            """)

    def observe(self, listing_key, payload):
        if not isinstance(listing_key, str) or not listing_key.strip():
            raise ValueError("Brak listing_key")

        if not isinstance(payload, dict):
            raise ValueError("Nieprawidlowa obserwacja")

        raw = canonical(payload)
        content_hash = hashlib.sha256(
            raw.encode()
        ).hexdigest()

        stamp = datetime.now(
            timezone.utc
        ).isoformat()

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")

            db.execute("""
                INSERT OR IGNORE INTO
                listing_observations (
                    listing_key,
                    content_hash,
                    payload_json,
                    observed_at
                )
                VALUES (?, ?, ?, ?)
            """, (
                listing_key,
                content_hash,
                raw,
                stamp,
            ))

            row = db.execute("""
                SELECT id FROM listing_observations
                WHERE listing_key=?
                  AND content_hash=?
            """, (
                listing_key,
                content_hash,
            )).fetchone()

            db.commit()

            return row["id"]

    def value(
        self,
        observation_id,
        engine_version,
        policy_version,
        market_snapshot_id,
        result,
    ):
        for version in (
            engine_version,
            policy_version,
            market_snapshot_id,
        ):
            if not isinstance(version, str) or not version.strip():
                raise ValueError("Brak wersji")

        raw = canonical(result)

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")

            existing = db.execute("""
                SELECT id, result_json
                FROM valuation_runs
                WHERE observation_id=?
                  AND engine_version=?
                  AND policy_version=?
                  AND market_snapshot_id=?
            """, (
                observation_id,
                engine_version,
                policy_version,
                market_snapshot_id,
            )).fetchone()

            if existing:
                if existing["result_json"] != raw:
                    raise ValueError(
                        "Zmien wersje silnika lub rynku"
                    )

                db.commit()
                return existing["id"]

            cursor = db.execute("""
                INSERT INTO valuation_runs (
                    observation_id,
                    engine_version,
                    policy_version,
                    market_snapshot_id,
                    result_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                observation_id,
                engine_version,
                policy_version,
                market_snapshot_id,
                raw,
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ))

            db.commit()
            return cursor.lastrowid

    def history(self, listing_key):
        with self.connect() as db:
            rows = db.execute("""
                SELECT
                    o.id AS observation_id,
                    o.observed_at,
                    o.payload_json,
                    v.id AS valuation_id,
                    v.engine_version,
                    v.policy_version,
                    v.market_snapshot_id,
                    v.result_json
                FROM listing_observations o
                LEFT JOIN valuation_runs v
                    ON v.observation_id=o.id
                WHERE o.listing_key=?
                ORDER BY o.id DESC, v.id DESC
                LIMIT 200
            """, (listing_key,)).fetchall()

            return [dict(row) for row in rows]
