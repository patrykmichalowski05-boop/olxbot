"""Transactional observations, evaluations and leased delivery queue.

This database is independent of the PC scanner and the PostgreSQL flip ledger.
Every query is scoped to the authenticated/configured owner.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import closing, contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .matching import matches, normalize, risks
from .models import Offer, Search, digest, now_iso, timestamp


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


SCHEMA = """
CREATE TABLE IF NOT EXISTS hunter_meta (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS hunter_searches (
 owner TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
 PRIMARY KEY(owner,id));
CREATE TABLE IF NOT EXISTS hunter_offers (
 owner TEXT NOT NULL, key TEXT NOT NULL, body TEXT NOT NULL,
 fingerprint TEXT NOT NULL, revision INTEGER NOT NULL, first_seen TEXT NOT NULL,
 last_seen TEXT NOT NULL, PRIMARY KEY(owner,key));
CREATE TABLE IF NOT EXISTS hunter_health (
 owner TEXT NOT NULL, search_id TEXT NOT NULL, platform TEXT NOT NULL,
 bootstrapped INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
 message TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
 failures INTEGER NOT NULL DEFAULT 0, checked_at TEXT NOT NULL, next_due TEXT,
 source_mode TEXT NOT NULL DEFAULT 'UNKNOWN',
 PRIMARY KEY(owner,search_id,platform));
CREATE TABLE IF NOT EXISTS hunter_matches (
 owner TEXT NOT NULL, search_id TEXT NOT NULL, offer_key TEXT NOT NULL,
 baseline_price INTEGER, last_alert_price INTEGER,
 PRIMARY KEY(owner,search_id,offer_key));
CREATE TABLE IF NOT EXISTS hunter_snapshots (
 id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,
 search_id TEXT NOT NULL, offer_key TEXT NOT NULL, result TEXT NOT NULL,
 fingerprint TEXT NOT NULL, created_at TEXT NOT NULL, offer_body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS hunter_snapshot_owner ON hunter_snapshots(owner,id DESC);
CREATE INDEX IF NOT EXISTS hunter_snapshot_match ON hunter_snapshots(owner,search_id,offer_key,id DESC);
CREATE TABLE IF NOT EXISTS hunter_outbox (
 id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, search_id TEXT NOT NULL,
 offer_key TEXT NOT NULL, price_minor INTEGER NOT NULL, body TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
 due_at TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
 lease_token TEXT, lease_until TEXT, last_error TEXT,
 UNIQUE(owner,search_id,offer_key,price_minor));
CREATE INDEX IF NOT EXISTS hunter_outbox_due ON hunter_outbox(owner,state,due_at);
CREATE TABLE IF NOT EXISTS hunter_delivery (owner TEXT PRIMARY KEY, blocked_until TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        forbidden = Path("/opt/olx-bot")
        if self.path == forbidden or forbidden in self.path.parents:
            raise ValueError(
                "Baza uniwersalna musi znajdować się poza katalogiem starego skanera"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        new = not self.path.exists()
        # Refuse to silently turn an existing legacy/auth database into a hunter DB.
        with closing(self.connect()) as db:
            tables = {
                r[0]
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if tables and "hunter_meta" not in tables:
                raise ValueError("Wybierz osobny plik bazy dla uniwersalnego skanera")
            if "hunter_meta" in tables:
                versions = list(db.execute("SELECT version FROM hunter_meta"))
                if len(versions) != 1 or versions[0][0] != 1:
                    raise ValueError("Nieobsługiwana wersja bazy skanera")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            if not tables:
                db.execute("INSERT INTO hunter_meta VALUES (1)")
                db.commit()
        if new:
            self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        db.create_function("hunter_normalize", 1, normalize, deterministic=True)
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def save_search(self, search: Search, connection=None):
        with (
            self.transaction() if connection is None else nullcontext(connection) as db
        ):
            previous = db.execute(
                "SELECT body FROM hunter_searches WHERE owner=? AND id=?",
                (search.owner_id, search.id),
            ).fetchone()

            def relevant(body):
                return {k: v for k, v in body.items() if k not in {"name", "enabled"}}

            if previous and digest(relevant(json.loads(previous["body"]))) != digest(
                relevant(search.payload())
            ):
                # A changed product/filter has a fresh baseline; old alerts and
                # calculations no longer describe the newly selected search.
                for table in ("hunter_health", "hunter_matches", "hunter_snapshots"):
                    db.execute(
                        f"DELETE FROM {table} WHERE owner=? AND search_id=?",
                        (search.owner_id, search.id),
                    )
                db.execute(
                    "UPDATE hunter_outbox SET state='CANCELLED' WHERE owner=? AND search_id=? AND state IN ('PENDING','RETRY')",
                    (search.owner_id, search.id),
                )
            db.execute(
                "INSERT INTO hunter_searches VALUES (?,?,?) ON CONFLICT(owner,id) DO UPDATE SET body=excluded.body",
                (search.owner_id, search.id, encode(search.payload())),
            )
            if not search.enabled:
                db.execute(
                    "UPDATE hunter_outbox SET state='CANCELLED',lease_token=NULL,lease_until=NULL WHERE owner=? AND search_id=? AND state IN ('PENDING','RETRY')",
                    (search.owner_id, search.id),
                )

    def searches(self, owner: str | None = None) -> list[Search]:
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT body FROM hunter_searches"
                + (" WHERE owner=?" if owner else "")
                + " ORDER BY owner,id",
                (owner,) if owner else (),
            ).fetchall()
        return [Search.from_mapping(json.loads(r["body"])) for r in rows]

    def delete_search(self, owner: str, search_id: str) -> bool:
        with self.transaction() as db:
            changed = db.execute(
                "DELETE FROM hunter_searches WHERE owner=? AND id=?", (owner, search_id)
            ).rowcount
            for table in ("hunter_health", "hunter_matches", "hunter_snapshots"):
                db.execute(
                    f"DELETE FROM {table} WHERE owner=? AND search_id=?",
                    (owner, search_id),
                )
            db.execute(
                "UPDATE hunter_outbox SET state='CANCELLED',lease_token=NULL,lease_until=NULL WHERE owner=? AND search_id=? AND state IN ('PENDING','RETRY')",
                (owner, search_id),
            )
        return bool(changed)

    def observe(self, owner: str, offers: list[Offer]):
        with self.transaction() as db:
            for offer in offers:
                if timestamp(offer.observed_at) > datetime.now(
                    timezone.utc
                ) + timedelta(minutes=5):
                    continue
                body = offer.payload()
                fingerprint = digest(
                    {k: v for k, v in body.items() if k != "observed_at"}
                )
                changed = db.execute(
                    """INSERT INTO hunter_offers VALUES (?,?,?,?,1,?,?)
                    ON CONFLICT(owner,key) DO UPDATE SET body=excluded.body,
                    revision=hunter_offers.revision+(hunter_offers.fingerprint!=excluded.fingerprint),
                    fingerprint=excluded.fingerprint,last_seen=excluded.last_seen
                    WHERE excluded.last_seen>=hunter_offers.last_seen""",
                    (
                        owner,
                        offer.key,
                        encode(body),
                        fingerprint,
                        offer.observed_at,
                        offer.observed_at,
                    ),
                ).rowcount
                if changed and offer.status != "ACTIVE":
                    db.execute(
                        "UPDATE hunter_outbox SET state='CANCELLED' WHERE owner=? AND offer_key=? AND state IN ('PENDING','RETRY')",
                        (owner, offer.key),
                    )

    def offers(
        self, owner: str, since: str | None = None, limit: int = 10000
    ) -> list[Offer]:
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT body FROM hunter_offers WHERE owner=?"
                + (" AND last_seen>=?" if since else "")
                + " ORDER BY last_seen DESC LIMIT ?",
                (owner, since, limit) if since else (owner, limit),
            ).fetchall()
        return [Offer.from_mapping(json.loads(r["body"])) for r in rows]

    def health(self, owner: str, search_id: str | None = None) -> list[dict]:
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT * FROM hunter_health WHERE owner=?"
                + (" AND search_id=?" if search_id else "")
                + " ORDER BY search_id,platform",
                (owner, search_id) if search_id else (owner,),
            ).fetchall()
        return [dict(row) for row in rows]

    def source_status(
        self,
        search: Search,
        platform: str,
        status: str,
        message: str,
        count: int = 0,
        retry_after: int = 0,
        now: str | None = None,
        mode: str = "UNKNOWN",
    ):
        now = timestamp(now or now_iso()).isoformat()
        with self.transaction() as db:
            old = db.execute(
                "SELECT * FROM hunter_health WHERE owner=? AND search_id=? AND platform=?",
                (search.owner_id, search.id, platform),
            ).fetchone()
            failures = (
                0 if status == "OK" else min(20, (old["failures"] if old else 0) + 1)
            )
            delay = (
                0
                if status == "OK"
                else max(retry_after, min(3600, 30 * 2 ** min(failures - 1, 7)))
            )
            next_due = (
                (timestamp(now) + timedelta(seconds=delay)).isoformat()
                if delay
                else None
            )
            db.execute(
                """INSERT INTO hunter_health VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(owner,search_id,platform) DO UPDATE SET
                bootstrapped=excluded.bootstrapped,status=excluded.status,message=excluded.message,
                count=excluded.count,failures=excluded.failures,checked_at=excluded.checked_at,next_due=excluded.next_due,source_mode=excluded.source_mode""",
                (
                    search.owner_id,
                    search.id,
                    platform,
                    int(status == "OK" or bool(old and old["bootstrapped"])),
                    status,
                    message[:240],
                    count,
                    failures,
                    now,
                    next_due,
                    mode,
                ),
            )

    def record(
        self,
        search: Search,
        offer: Offer,
        result: dict,
        initial: bool,
        now: str | None = None,
        allow_alerts: bool = True,
    ) -> bool:
        """Snapshot and unique alert insertion commit together, including baseline."""
        now = timestamp(now or now_iso()).isoformat()
        with self.transaction() as db:
            old = db.execute(
                "SELECT * FROM hunter_matches WHERE owner=? AND search_id=? AND offer_key=?",
                (search.owner_id, search.id, offer.key),
            ).fetchone()
            baseline = (
                old["baseline_price"]
                if old
                else (
                    offer.price_minor if initial and not search.notify_initial else None
                )
            )
            last_alert = old["last_alert_price"] if old else None
            db.execute(
                "INSERT OR IGNORE INTO hunter_matches VALUES (?,?,?,?,?)",
                (search.owner_id, search.id, offer.key, baseline, last_alert),
            )
            fingerprint = digest(
                {
                    "result": result,
                    "offer": {
                        k: v for k, v in offer.payload().items() if k != "observed_at"
                    },
                }
            )
            previous = db.execute(
                "SELECT fingerprint FROM hunter_snapshots WHERE owner=? AND search_id=? AND offer_key=? ORDER BY id DESC LIMIT 1",
                (search.owner_id, search.id, offer.key),
            ).fetchone()
            if previous is None or previous["fingerprint"] != fingerprint:
                db.execute(
                    "INSERT INTO hunter_snapshots(owner,search_id,offer_key,result,fingerprint,created_at,offer_body) VALUES (?,?,?,?,?,?,?)",
                    (
                        search.owner_id,
                        search.id,
                        offer.key,
                        encode(result),
                        fingerprint,
                        now,
                        encode(offer.payload()),
                    ),
                )
            if not result.get("qualifies"):
                db.execute(
                    "UPDATE hunter_outbox SET state='CANCELLED' WHERE owner=? AND search_id=? AND offer_key=? AND state IN ('PENDING','RETRY')",
                    (search.owner_id, search.id, offer.key),
                )
            eligible = (
                allow_alerts
                and search.enabled
                and result.get("qualifies") is True
                and offer.status == "ACTIVE"
                and offer.price_minor is not None
                and offer.price_minor > 0
                and (
                    baseline is None
                    or offer.price_minor < baseline
                    or search.notify_initial
                )
                and (last_alert is None or offer.price_minor < last_alert)
            )
            if not eligible:
                return False
            payload = {
                "offer": offer.payload(),
                "result": result,
                "search_id": search.id,
                "search_name": search.name,
            }
            inserted = db.execute(
                """INSERT OR IGNORE INTO hunter_outbox
                (owner,search_id,offer_key,price_minor,body,due_at,created_at,expires_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    search.owner_id,
                    search.id,
                    offer.key,
                    offer.price_minor,
                    encode(payload),
                    now,
                    now,
                    (timestamp(now) + timedelta(hours=6)).isoformat(),
                ),
            ).rowcount
            if inserted:
                db.execute(
                    "UPDATE hunter_matches SET last_alert_price=? WHERE owner=? AND search_id=? AND offer_key=?",
                    (offer.price_minor, search.owner_id, search.id, offer.key),
                )
            return bool(inserted)

    def claim(
        self, owner: str, now: str | None = None, lease_seconds: int = 90
    ) -> dict | None:
        now = timestamp(now or now_iso()).isoformat()
        with self.transaction() as db:
            cooldown = db.execute(
                "SELECT blocked_until FROM hunter_delivery WHERE owner=?", (owner,)
            ).fetchone()
            if cooldown and cooldown["blocked_until"] > now:
                return None
            db.execute(
                "UPDATE hunter_outbox SET state='EXPIRED',lease_token=NULL,lease_until=NULL WHERE owner=? AND expires_at<=? AND state IN ('PENDING','RETRY','CLAIMED')",
                (owner, now),
            )
            db.execute(
                "UPDATE hunter_outbox SET state='RETRY',lease_token=NULL,lease_until=NULL WHERE owner=? AND state='CLAIMED' AND lease_until<=?",
                (owner, now),
            )
            rows = db.execute(
                "SELECT * FROM hunter_outbox WHERE owner=? AND state IN ('PENDING','RETRY') AND due_at<=? ORDER BY id LIMIT 100",
                (owner, now),
            ).fetchall()
            for row in rows:
                current = db.execute(
                    "SELECT body FROM hunter_offers WHERE owner=? AND key=?",
                    (owner, row["offer_key"]),
                ).fetchone()
                profile = db.execute(
                    "SELECT body FROM hunter_searches WHERE owner=? AND id=?",
                    (owner, row["search_id"]),
                ).fetchone()
                offer = json.loads(current["body"]) if current else {}
                enabled = bool(profile and json.loads(profile["body"])["enabled"])
                latest = db.execute(
                    "SELECT result FROM hunter_snapshots WHERE owner=? AND search_id=? AND offer_key=? ORDER BY id DESC LIMIT 1",
                    (owner, row["search_id"], row["offer_key"]),
                ).fetchone()
                valid_result = bool(
                    latest and json.loads(latest["result"]).get("qualifies")
                )
                fresh = bool(
                    offer
                    and timestamp(offer["observed_at"])
                    >= timestamp(now) - timedelta(hours=6)
                )
                valid_model = bool(
                    offer
                    and profile
                    and matches(
                        Offer.from_mapping(offer),
                        Search.from_mapping(json.loads(profile["body"])),
                    )
                    and not risks(Offer.from_mapping(offer))
                )
                if (
                    not enabled
                    or not fresh
                    or not valid_result
                    or not valid_model
                    or offer.get("status") != "ACTIVE"
                    or offer.get("price_minor") != row["price_minor"]
                ):
                    db.execute(
                        "UPDATE hunter_outbox SET state='CANCELLED' WHERE id=?",
                        (row["id"],),
                    )
                    continue
                token = secrets.token_urlsafe(24)
                until = (timestamp(now) + timedelta(seconds=lease_seconds)).isoformat()
                db.execute(
                    "UPDATE hunter_outbox SET state='CLAIMED',attempts=attempts+1,lease_token=?,lease_until=? WHERE id=?",
                    (token, until, row["id"]),
                )
                return {
                    **dict(row),
                    "body": json.loads(row["body"]),
                    "lease_token": token,
                    "lease_until": until,
                    "attempts": row["attempts"] + 1,
                }
        return None

    def finish(
        self,
        alert: dict,
        state: str = "DONE",
        error: str | None = None,
        retry_after: int = 0,
        now: str | None = None,
    ) -> bool:
        if state not in {"DONE", "RETRY", "FAILED"}:
            raise ValueError("Nieprawidłowy stan dostarczenia")
        now = timestamp(now or now_iso()).isoformat()
        due = (timestamp(now) + timedelta(seconds=max(1, retry_after))).isoformat()
        with self.transaction() as db:
            return bool(
                db.execute(
                    """UPDATE hunter_outbox SET state=?,last_error=?,due_at=?,lease_token=NULL,lease_until=NULL
                WHERE id=? AND owner=? AND state='CLAIMED' AND lease_token=? AND lease_until>?""",
                    (
                        state,
                        error,
                        due,
                        alert["id"],
                        alert["owner"],
                        alert["lease_token"],
                        now,
                    ),
                ).rowcount
            )

    def queue_summary(self, owner: str) -> dict:
        with closing(self.connect()) as db:
            return {
                r["state"]: r["n"]
                for r in db.execute(
                    "SELECT state,count(*) n FROM hunter_outbox WHERE owner=? GROUP BY state",
                    (owner,),
                )
            }

    def defer_notifications(self, owner: str, seconds: int):
        due = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        with self.transaction() as db:
            db.execute(
                "INSERT INTO hunter_delivery VALUES (?,?) ON CONFLICT(owner) DO UPDATE SET blocked_until=max(blocked_until,excluded.blocked_until)",
                (owner, due),
            )
            db.execute(
                "UPDATE hunter_outbox SET due_at=? WHERE owner=? AND state IN ('PENDING','RETRY') AND due_at<?",
                (due, owner, due),
            )

    def retry_failed(self, owner: str) -> int:
        now = now_iso()
        with self.transaction() as db:
            return db.execute(
                "UPDATE hunter_outbox SET state='RETRY',attempts=0,due_at=?,last_error=NULL WHERE owner=? AND state='FAILED' AND expires_at>?",
                (now, owner, now),
            ).rowcount

    def radar(
        self, owner: str, query: str = "", limit: int = 20, before_id: int | None = None
    ) -> dict:
        # Rank before pagination to avoid resurfacing historical versions.
        sql = """WITH ranked AS (
            SELECT s.*,o.body,ROW_NUMBER() OVER(PARTITION BY s.offer_key ORDER BY s.id DESC) rn
            FROM hunter_snapshots s JOIN hunter_offers o ON o.owner=s.owner AND o.key=s.offer_key
            JOIN hunter_searches p ON p.owner=s.owner AND p.id=s.search_id
            WHERE s.owner=? AND json_extract(p.body,'$.enabled')=1)
            SELECT * FROM ranked WHERE rn=1 AND json_extract(body,'$.status')='ACTIVE'
            AND instr(hunter_normalize(json_extract(body,'$.title')),hunter_normalize(?))>0"""
        params = [owner, query]
        if before_id:
            sql += " AND id<?"
            params.append(before_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit + 1)
        with closing(self.connect()) as db:
            rows = db.execute(sql, params).fetchall()
        items = [self._mobile(row) for row in rows[:limit]]
        return {
            "items": items,
            "next_before_id": items[-1]["snapshot_id"] if len(rows) > limit else None,
        }

    def detail(self, owner: str, snapshot_id: int) -> dict | None:
        with closing(self.connect()) as db:
            row = db.execute(
                """SELECT s.*,o.body FROM hunter_snapshots s
                JOIN hunter_offers o ON o.owner=s.owner AND o.key=s.offer_key
                JOIN hunter_searches p ON p.owner=s.owner AND p.id=s.search_id
                WHERE s.owner=? AND s.id=? AND json_extract(p.body,'$.enabled')=1""",
                (owner, snapshot_id),
            ).fetchone()
        return self._mobile(row) if row else None

    @staticmethod
    def _mobile(row) -> dict:
        offer, result = json.loads(row["body"]), json.loads(row["result"])
        original = json.loads(row["offer_body"])
        # Never attach an old prediction to a changed price/model. The next
        # successful evaluation replaces it; until then show unknown economics.
        if any(
            offer.get(key) != original.get(key)
            for key in (
                "price_minor",
                "title",
                "attributes",
                "condition",
                "price_kind",
                "status",
            )
        ):
            result = {
                **result,
                "valuation": None,
                "market": None,
                "decision": "NO_RELIABLE_VALUATION",
                "insight": "Dane oferty zmieniły się. Oczekiwanie na ponowną wycenę.",
            }
        value = result.get("valuation") or {}

        def major(key):
            return value[key] / 100 if key in value else None

        valuation = {
            "quick_sale": major("sell_minor"),
            "profit": major("profit_minor"),
            "max_buy": major("max_buy_minor"),
            "roi": value.get("roi_bps", 0) / 100,
            "total_cost": major("cost_minor"),
            "roi_bps": value.get("roi_bps"),
            "confidence": (result.get("market") or {}).get("confidence"),
            "image_url": offer.get("image_url"),
            "category": result["category"],
            "issues": result.get("warnings", []),
            "summary": result["insight"],
            "analysis_source": "RULES_AND_COMPARABLES",
            "market": result.get("market"),
            "costs_minor": value.get("costs"),
            "profit_after_tax": False,
        }
        return {
            "snapshot_id": row["id"],
            "title": offer["title"],
            "platform": offer["platform"],
            "decision": result["decision"],
            "valuation": valuation,
            "observed_at": offer["observed_at"],
            "price_minor": offer["price_minor"],
            "url": offer["url"],
        }
