import hashlib
import json
import sqlite3
import uuid

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .money import valid_minor


COST_KINDS = {
    "TRANSPORT_BUY",
    "REPAIR",
    "PREPARATION",
    "FEE",
    "TRANSPORT_SALE",
    "RISK_RESERVE",
    "OTHER",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class DealLedger:

    def __init__(self, db_path):
        self.path = Path(db_path).expanduser().resolve()

    def connect(self):
        conn = sqlite3.connect(
            str(self.path),
            timeout=15,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")

        return conn

    @contextmanager
    def transaction(self):
        conn = self.connect()

        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.transaction() as db:
            schema_sql = """
                CREATE TABLE IF NOT EXISTS deals (
                    id TEXT PRIMARY KEY,
                    product_instance_id TEXT NOT NULL UNIQUE,
                    purchase_minor INTEGER NOT NULL
                        CHECK(purchase_minor > 0),
                    sale_minor INTEGER
                        CHECK(sale_minor > 0),
                    currency TEXT NOT NULL
                        CHECK(currency = 'PLN'),
                    status TEXT NOT NULL
                        CHECK(status IN ('BOUGHT', 'SOLD')),
                    purchased_at TEXT NOT NULL,
                    sold_at TEXT
                );

                CREATE TABLE IF NOT EXISTS deal_costs (
                    id TEXT PRIMARY KEY,
                    deal_id TEXT NOT NULL REFERENCES deals(id),
                    kind TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL
                        CHECK(amount_minor >= 0),
                    currency TEXT NOT NULL
                        CHECK(currency = 'PLN'),
                    note TEXT NOT NULL DEFAULT '',
                    occurred_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_deal_costs_deal
                    ON deal_costs(deal_id);

                CREATE TABLE IF NOT EXISTS
                    idempotency_results (
                    key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    response TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS
                    notification_outbox (
                    id TEXT PRIMARY KEY,
                    deal_id TEXT NOT NULL REFERENCES deals(id),
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT
                );
            """
            for statement in schema_sql.split(";"):
                if statement.strip():
                    db.execute(statement)

    def _run(self, key, operation, data, work):
        if (
            not isinstance(key, str)
            or not 8 <= len(key) <= 128
        ):
            raise ValueError("Nieprawidlowy Idempotency-Key")

        fingerprint = hashlib.sha256(
            json.dumps(
                data,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        with self.transaction() as db:
            existing = db.execute("""
                SELECT operation, fingerprint, response
                FROM idempotency_results
                WHERE key=?
            """, (key,)).fetchone()

            if existing:
                if (
                    existing["operation"] != operation
                    or existing["fingerprint"] != fingerprint
                ):
                    raise ValueError(
                        "Klucz uzyty z innymi danymi"
                    )

                return json.loads(existing["response"])

            response = work(db)

            db.execute("""
                INSERT INTO idempotency_results
                VALUES (?, ?, ?, ?)
            """, (
                key,
                operation,
                fingerprint,
                json.dumps(response, sort_keys=True),
            ))

            return response

    def _event(self, db, deal_id, kind, payload):
        db.execute("""
            INSERT INTO notification_outbox (
                id,
                deal_id,
                event_type,
                payload_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            deal_id,
            kind,
            json.dumps(payload, sort_keys=True),
            utc_now(),
        ))

    def purchase(
        self,
        product_instance_id,
        price_minor,
        *,
        key,
    ):
        valid_minor(price_minor, positive=True)

        if (
            not isinstance(product_instance_id, str)
            or not product_instance_id.strip()
        ):
            raise ValueError("Brak product_instance_id")

        data = {
            "instance": product_instance_id,
            "price": price_minor,
        }

        def work(db):
            deal_id = str(uuid.uuid4())

            db.execute("""
                INSERT INTO deals (
                    id,
                    product_instance_id,
                    purchase_minor,
                    currency,
                    status,
                    purchased_at
                )
                VALUES (?, ?, ?, 'PLN', 'BOUGHT', ?)
            """, (
                deal_id,
                product_instance_id.strip(),
                price_minor,
                utc_now(),
            ))

            self._event(
                db,
                deal_id,
                "DEAL_PURCHASED",
                {"purchase_minor": price_minor},
            )

            return {
                "deal_id": deal_id,
                "status": "BOUGHT",
            }

        try:
            return self._run(
                key,
                "purchase",
                data,
                work,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Ten egzemplarz jest juz kupiony"
            ) from exc

    def add_cost(
        self,
        deal_id,
        kind,
        amount_minor,
        *,
        key,
        note="",
    ):
        valid_minor(amount_minor)

        if kind not in COST_KINDS:
            raise ValueError("Nieznany rodzaj kosztu")

        data = {
            "deal_id": deal_id,
            "kind": kind,
            "amount": amount_minor,
            "note": str(note),
        }

        def work(db):
            row = db.execute("""
                SELECT 1 FROM deals WHERE id=?
            """, (deal_id,)).fetchone()

            if not row:
                raise ValueError("Nie znaleziono flipa")

            cost_id = str(uuid.uuid4())

            db.execute("""
                INSERT INTO deal_costs (
                    id,
                    deal_id,
                    kind,
                    amount_minor,
                    currency,
                    note,
                    occurred_at
                )
                VALUES (?, ?, ?, ?, 'PLN', ?, ?)
            """, (
                cost_id,
                deal_id,
                kind,
                amount_minor,
                str(note),
                utc_now(),
            ))

            return {
                "cost_id": cost_id,
                "deal_id": deal_id,
            }

        return self._run(
            key,
            "cost",
            data,
            work,
        )

    def sell(
        self,
        deal_id,
        price_minor,
        *,
        key,
    ):
        valid_minor(price_minor, positive=True)

        data = {
            "deal_id": deal_id,
            "price": price_minor,
        }

        def work(db):
            updated = db.execute("""
                UPDATE deals
                SET sale_minor=?,
                    status='SOLD',
                    sold_at=?
                WHERE id=?
                  AND status='BOUGHT'
            """, (
                price_minor,
                utc_now(),
                deal_id,
            ))

            if updated.rowcount != 1:
                raise ValueError(
                    "Flip nie istnieje lub juz sprzedany"
                )

            self._event(
                db,
                deal_id,
                "DEAL_SOLD",
                {"sale_minor": price_minor},
            )

            return {
                "deal_id": deal_id,
                "status": "SOLD",
            }

        return self._run(
            key,
            "sale",
            data,
            work,
        )

    def get(self, deal_id):
        conn = self.connect()

        try:
            row = conn.execute("""
                SELECT * FROM deals WHERE id=?
            """, (deal_id,)).fetchone()

            if row is None:
                return None

            result = dict(row)

            total = conn.execute("""
                SELECT COALESCE(SUM(amount_minor), 0)
                FROM deal_costs
                WHERE deal_id=?
            """, (deal_id,)).fetchone()[0]

            result["total_cost_minor"] = total

            if result["sale_minor"] is None:
                result["realized_profit_minor"] = None
            else:
                result["realized_profit_minor"] = (
                    result["sale_minor"]
                    - result["purchase_minor"]
                    - total
                )

            return result

        finally:
            conn.close()
