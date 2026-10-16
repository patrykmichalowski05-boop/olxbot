from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from flip_core.auth_store import AuthStore, token_hash
from universal_v2.hunter.models import Search, digest
from universal_v2.hunter.store import Store

from .plans import PLANS, PUBLIC_PLANS

SCHEMA = """
CREATE TABLE IF NOT EXISTS portal_accounts (
 user_id TEXT PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, plan TEXT NOT NULL,
 grant_id TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
 expires_at INTEGER, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS portal_usage (
 user_id TEXT NOT NULL, grant_id TEXT NOT NULL, operation TEXT NOT NULL,
 request_hash TEXT NOT NULL, response TEXT, created_at INTEGER NOT NULL,
 PRIMARY KEY(user_id,grant_id,operation));
CREATE TABLE IF NOT EXISTS portal_browser_sessions (
 hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL,
 revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS portal_browser_links (
 browser_hash TEXT NOT NULL, auth_session TEXT NOT NULL,
 PRIMARY KEY(browser_hash,auth_session));
CREATE TABLE IF NOT EXISTS portal_guests (
 hash TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS portal_guest_requests (
 guest_hash TEXT NOT NULL, operation TEXT NOT NULL, request_hash TEXT NOT NULL,
 response TEXT NOT NULL, PRIMARY KEY(guest_hash,operation));
CREATE TABLE IF NOT EXISTS portal_limits (
 scope TEXT NOT NULL, identity TEXT NOT NULL, bucket INTEGER NOT NULL,
 used INTEGER NOT NULL, PRIMARY KEY(scope,identity,bucket));
CREATE TABLE IF NOT EXISTS portal_plan_requests (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL,
 status TEXT NOT NULL, created_at INTEGER NOT NULL, resolved_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS portal_one_pending_plan
 ON portal_plan_requests(user_id) WHERE status='PENDING';
CREATE TABLE IF NOT EXISTS portal_meta (name TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS portal_admin_actions (
 operation TEXT PRIMARY KEY, actor TEXT NOT NULL, request_hash TEXT NOT NULL,
 response TEXT NOT NULL, created_at INTEGER NOT NULL);
"""


class AccessDenied(ValueError):
    def __init__(self, code, message, status=402):
        super().__init__(message)
        self.code, self.status = code, status


class PortalStore:
    def __init__(
        self,
        store: Store,
        auth: AuthStore,
        owner_id: str | None = None,
        clock=time.time,
    ):
        self.store, self.auth, self.clock = store, auth, clock
        with self.store.transaction() as db:
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    db.execute(statement)
            db.execute(
                "INSERT OR IGNORE INTO portal_meta VALUES (?,?)",
                ("ip_salt", secrets.token_hex(32)),
            )
        # Existing installations keep their previous access. Public registration
        # below always creates START members; it cannot become an owner.
        with self.auth.transaction() as db:
            existing = db.execute(
                "SELECT id,username FROM users ORDER BY rowid"
            ).fetchall()
        with self.store.transaction() as db:
            migrated = db.execute(
                "SELECT 1 FROM portal_meta WHERE name='legacy_migrated'"
            ).fetchone()
            if not migrated:
                if not existing:
                    raise RuntimeError(
                        "Najpierw utwórz konto właściciela przez bootstrap, potem włącz portal."
                    )
                if owner_id and owner_id not in {row["id"] for row in existing}:
                    raise RuntimeError(
                        "FLIP_PORTAL_OWNER_ID nie wskazuje istniejącego konta."
                    )
                initial_owner = owner_id or (existing[0]["id"] if existing else None)
                for row in existing:
                    db.execute(
                        """INSERT OR IGNORE INTO portal_accounts
                        VALUES (?,?,?,1,'LEGACY',?,0,NULL,?)""",
                        (
                            row["id"],
                            row["username"],
                            "OWNER" if row["id"] == initial_owner else "MEMBER",
                            uuid.uuid4().hex,
                            int(self.clock()),
                        ),
                    )
                db.execute("INSERT INTO portal_meta VALUES ('legacy_migrated','1')")

    def ip_key(self, address: str) -> str:
        with self.store.transaction() as db:
            salt = db.execute(
                "SELECT value FROM portal_meta WHERE name='ip_salt'"
            ).fetchone()[0]
        return hmac.new(salt.encode(), address.encode(), hashlib.sha256).hexdigest()

    def rate_limit(self, scope, identity, limit, seconds):
        now = int(self.clock())
        bucket = now // seconds
        denied = False
        with self.store.transaction() as db:
            db.execute(
                "DELETE FROM portal_limits WHERE bucket<? AND scope=?",
                (bucket - 2, scope),
            )
            row = db.execute(
                "SELECT used FROM portal_limits WHERE scope=? AND identity=? AND bucket=?",
                (scope, identity, bucket),
            ).fetchone()
            if row and row["used"] >= limit:
                denied = True
            else:
                db.execute(
                    """INSERT INTO portal_limits VALUES (?,?,?,1)
                    ON CONFLICT(scope,identity,bucket) DO UPDATE SET used=used+1""",
                    (scope, identity, bucket),
                )
        if denied:
            raise AccessDenied(
                "RATE_LIMITED", "Zbyt wiele prób. Spróbuj ponownie później.", 429
            )

    def register(self, username, password):
        # Create a member row BEFORE exposing credentials. If provisioning fails,
        # no access token is returned and the account remains without access.
        user_id = self.auth.register_user(username, password)
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO portal_accounts VALUES (?,?,'MEMBER',1,'START',?,0,NULL,?)",
                (
                    user_id,
                    username.strip().lower(),
                    uuid.uuid4().hex,
                    int(self.clock()),
                ),
            )
        return user_id

    def login_name(self, username):
        """Normalize registered names, preserving exact legacy-name matches."""
        username = username.strip()
        with self.store.transaction() as db:
            row = db.execute(
                """SELECT username FROM portal_accounts WHERE lower(username)=?
                ORDER BY CASE WHEN username=? THEN 0 ELSE 1 END LIMIT 1""",
                (username.lower(), username),
            ).fetchone()
        return row["username"] if row else username.lower()

    def _account(self, db, user_id):
        row = db.execute(
            "SELECT * FROM portal_accounts WHERE user_id=?", (user_id,)
        ).fetchone()
        if row is None:
            raise AccessDenied(
                "ACCOUNT_NOT_PROVISIONED",
                "To konto nie ma jeszcze przypisanego dostępu.",
                403,
            )
        return dict(row)

    def _access(self, row):
        plan = PLANS[row["plan"]]
        active = bool(row["enabled"]) and (
            row["expires_at"] is None or row["expires_at"] > int(self.clock())
        )
        remaining = (
            None if plan.searches is None else max(0, plan.searches - row["used"])
        )
        return {
            "can_open_bot": active,
            "can_search": active and (remaining is None or remaining > 0),
            "can_receive_notifications": active and plan.notifications,
            "reason": "ACTIVE"
            if active
            else "DISABLED"
            if not row["enabled"]
            else "EXPIRED",
            "remaining": remaining,
            "limit": plan.searches,
            "used": row["used"],
            "expires_at": datetime.fromtimestamp(
                row["expires_at"], timezone.utc
            ).isoformat()
            if row["expires_at"]
            else None,
        }

    def account(self, user_id):
        with self.store.transaction() as db:
            row = self._account(db, user_id)
            request = db.execute(
                "SELECT id,plan,status,created_at FROM portal_plan_requests WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "role": row["role"],
            "plan": PLANS[row["plan"]].payload(),
            "access": self._access(row),
            "plan_request": dict(request) if request else None,
        }

    def require_bot(self, user_id):
        account = self.account(user_id)
        if not account["access"]["can_open_bot"]:
            raise AccessDenied(
                account["access"]["reason"],
                "Dostęp do bota jest nieaktywny. Sprawdź swój pakiet.",
                403,
            )
        return account

    def _consume(self, db, user_id, operation, request_hash):
        if not isinstance(operation, str) or not re.fullmatch(
            r"[A-Za-z0-9_.:-]{8,150}", operation
        ):
            raise ValueError("Nieprawidłowy identyfikator operacji")
        row = self._account(db, user_id)
        access = self._access(row)
        if not access["can_open_bot"]:
            raise AccessDenied(
                access["reason"], "Twój dostęp jest nieaktywny. Sprawdź pakiet.", 403
            )
        previous = db.execute(
            "SELECT * FROM portal_usage WHERE user_id=? AND grant_id=? AND operation=?",
            (user_id, row["grant_id"], operation),
        ).fetchone()
        if previous:
            if previous["request_hash"] != request_hash:
                raise AccessDenied(
                    "IDEMPOTENCY_CONFLICT",
                    "Ta operacja dotyczy innych danych. Ponów wyszukiwanie.",
                    409,
                )
            return row, previous
        if not access["can_search"]:
            raise AccessDenied(
                "QUOTA_EXHAUSTED",
                "Wykorzystano wyszukiwania w tym pakiecie. Wybierz kolejny pakiet.",
            )
        db.execute(
            "INSERT INTO portal_usage VALUES (?,?,?,?,NULL,?)",
            (user_id, row["grant_id"], operation, request_hash, int(self.clock())),
        )
        db.execute("UPDATE portal_accounts SET used=used+1 WHERE user_id=?", (user_id,))
        return row, None

    def save_search(self, search: Search):
        criteria = {
            key: value
            for key, value in search.payload().items()
            if key
            in {
                "query",
                "platforms",
                "category",
                "required_terms",
                "excluded_terms",
                "variant_keys",
                "attributes",
                "source_urls",
            }
        }
        with self.store.transaction() as db:
            access = self._access(self._account(db, search.owner_id))
            if not access["can_open_bot"]:
                raise AccessDenied(
                    access["reason"],
                    "Dostęp jest nieaktywny. Sprawdź swój pakiet.",
                    403,
                )
            previous = db.execute(
                "SELECT body FROM hunter_searches WHERE owner=? AND id=?",
                (search.owner_id, search.id),
            ).fetchone()
            old = json.loads(previous["body"]) if previous else None
            changed = not old or digest(
                {key: old.get(key) for key in criteria}
            ) != digest(criteria)
            if changed:
                self._consume(
                    db,
                    search.owner_id,
                    "profile:" + search.id + ":" + digest(criteria)[:32],
                    digest(criteria),
                )
            # Search, quota and usage ledger share the same SQLite transaction.
            self.store.save_search(search, connection=db)

    def request_plan(self, user_id, plan):
        if plan not in {"STANDARD", "PLUS"}:
            raise ValueError("Wybierz Standard lub Plus")
        with self.store.transaction() as db:
            self._account(db, user_id)
            existing = db.execute(
                "SELECT * FROM portal_plan_requests WHERE user_id=? AND status='PENDING'",
                (user_id,),
            ).fetchone()
            if existing:
                db.execute(
                    "UPDATE portal_plan_requests SET plan=? WHERE id=?",
                    (plan, existing["id"]),
                )
                return {"id": existing["id"], "plan": plan, "status": "PENDING"}
            identity = uuid.uuid4().hex
            db.execute(
                "INSERT INTO portal_plan_requests VALUES (?,?,?,'PENDING',?,NULL)",
                (identity, user_id, plan, int(self.clock())),
            )
        return {"id": identity, "plan": plan, "status": "PENDING"}

    def grant(self, user_id, plan, enabled=True):
        if plan not in PUBLIC_PLANS:
            raise ValueError("Nieprawidłowy pakiet")
        period = PLANS[plan].days
        expires = int(self.clock()) + period * 86400 if period else None
        with self.store.transaction() as db:
            row = self._account(db, user_id)
            if row["role"] == "OWNER":
                raise ValueError("Konto właściciela zachowuje oddzielny dostęp")
            db.execute(
                "UPDATE portal_accounts SET plan=?,grant_id=?,used=0,expires_at=?,enabled=? WHERE user_id=?",
                (plan, uuid.uuid4().hex, expires, int(enabled), user_id),
            )
            db.execute(
                "UPDATE portal_plan_requests SET status='APPROVED',resolved_at=? WHERE user_id=? AND status='PENDING' AND plan=?",
                (int(self.clock()), user_id, plan),
            )

    def disable(self, user_id):
        with self.store.transaction() as db:
            row = self._account(db, user_id)
            if row["role"] == "OWNER":
                raise ValueError(
                    "Nie można zablokować konta właściciela tym poleceniem"
                )
            db.execute(
                "UPDATE portal_accounts SET enabled=0 WHERE user_id=?", (user_id,)
            )
            db.execute(
                "UPDATE portal_browser_sessions SET revoked=1 WHERE user_id=?",
                (user_id,),
            )
        with self.auth.transaction() as db:
            db.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))

    def admin_access(self, actor, operation, user_id, action, plan=None):
        request_hash = digest({"user_id": user_id, "action": action, "plan": plan})
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,150}", operation):
            raise ValueError("Nieprawidłowy identyfikator operacji")
        with self.store.transaction() as db:
            owner = self._account(db, actor)
            if owner["role"] != "OWNER" or not owner["enabled"]:
                raise AccessDenied(
                    "FORBIDDEN", "Brak uprawnień do zarządzania dostępem.", 403
                )
            previous = db.execute(
                "SELECT * FROM portal_admin_actions WHERE operation=?", (operation,)
            ).fetchone()
            if previous:
                if (
                    previous["request_hash"] != request_hash
                    or previous["actor"] != actor
                ):
                    raise AccessDenied(
                        "IDEMPOTENCY_CONFLICT",
                        "Ta operacja dotyczy innych danych.",
                        409,
                    )
                return json.loads(previous["response"])
            member = self._account(db, user_id)
            if member["role"] == "OWNER":
                raise ValueError("Nie można zmienić dostępu konta właściciela")
            if action == "activate" and plan in PUBLIC_PLANS:
                days = PLANS[plan].days
                expires = int(self.clock()) + days * 86400 if days else None
                db.execute(
                    "UPDATE portal_accounts SET plan=?,grant_id=?,used=0,expires_at=?,enabled=1 WHERE user_id=?",
                    (plan, uuid.uuid4().hex, expires, user_id),
                )
                db.execute(
                    "UPDATE portal_plan_requests SET status='APPROVED',resolved_at=? WHERE user_id=? AND status='PENDING'",
                    (int(self.clock()), user_id),
                )
            elif action == "disable":
                db.execute(
                    "UPDATE portal_accounts SET enabled=0 WHERE user_id=?", (user_id,)
                )
                db.execute(
                    "UPDATE portal_browser_sessions SET revoked=1 WHERE user_id=?",
                    (user_id,),
                )
            else:
                raise ValueError("Nieprawidłowa zmiana dostępu")
            response = {
                "updated": True,
                "user_id": user_id,
                "action": action,
                "plan": plan,
            }
            db.execute(
                "INSERT INTO portal_admin_actions VALUES (?,?,?,?,?)",
                (
                    operation,
                    actor,
                    request_hash,
                    json.dumps(response),
                    int(self.clock()),
                ),
            )
        if action == "disable":
            with self.auth.transaction() as db:
                db.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))
        return response

    def admin_list(self, actor):
        with self.store.transaction() as db:
            if self._account(db, actor)["role"] != "OWNER":
                raise AccessDenied(
                    "FORBIDDEN", "Brak uprawnień do zarządzania kontami.", 403
                )
            accounts = [
                dict(r)
                for r in db.execute(
                    "SELECT user_id,username,role,enabled,plan,used,expires_at FROM portal_accounts ORDER BY created_at DESC,user_id LIMIT 500"
                )
            ]
            requests = [
                dict(r)
                for r in db.execute("""SELECT r.id,r.user_id,a.username,r.plan,r.status,r.created_at
                FROM portal_plan_requests r JOIN portal_accounts a ON a.user_id=r.user_id
                WHERE r.status='PENDING' ORDER BY r.created_at LIMIT 500""")
            ]
        return {"accounts": accounts, "requests": requests}

    def inbox(self, user_id, before_id=None, limit=30):
        self.require_bot(user_id)
        with self.store.transaction() as db:
            sql = "SELECT id,body,created_at FROM hunter_outbox WHERE owner=? AND state NOT IN ('CANCELLED','EXPIRED')"
            parameters = [user_id]
            if before_id:
                sql += " AND id<?"
                parameters.append(before_id)
            sql += " ORDER BY id DESC LIMIT ?"
            parameters.append(limit + 1)
            rows = db.execute(sql, parameters).fetchall()
        items = []
        for row in rows[:limit]:
            body = json.loads(row["body"])
            offer, result = body["offer"], body["result"]
            items.append(
                {
                    "id": str(row["id"]),
                    "category": "Okazja",
                    "title": offer["title"],
                    "reason": result["insight"],
                    "at": row["created_at"],
                }
            )
        return {
            "items": items,
            "next_before_id": items[-1]["id"] if len(rows) > limit else None,
        }

    def create_browser_session(self, user_id, access_token):
        cookie = secrets.token_urlsafe(32)
        with self.auth.transaction() as db:
            auth_row = self.auth._lookup(db, access_token, "access")
            if auth_row["user_id"] != user_id:
                raise ValueError("Nieprawidłowa sesja")
        with self.store.transaction() as db:
            self._account(db, user_id)
            db.execute(
                "INSERT INTO portal_browser_sessions VALUES (?,?,?,0)",
                (token_hash(cookie), user_id, int(self.clock()) + 7 * 86400),
            )
            db.execute(
                "INSERT INTO portal_browser_links VALUES (?,?)",
                (token_hash(cookie), auth_row["session_id"]),
            )
        return cookie

    def resume_browser(self, cookie):
        if not isinstance(cookie, str) or not 32 <= len(cookie) <= 200:
            raise AccessDenied("SESSION_EXPIRED", "Zaloguj się ponownie.", 401)
        # Keep the browser session stable across tabs; each resume has its own
        # Bearer family. Native refresh replay protection remains unchanged.
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM portal_browser_sessions WHERE hash=?",
                (token_hash(cookie),),
            ).fetchone()
            if not row or row["revoked"] or row["expires_at"] <= self.clock():
                raise AccessDenied("SESSION_EXPIRED", "Zaloguj się ponownie.", 401)
            account = self._account(db, row["user_id"])
            if not account["enabled"]:
                raise AccessDenied(
                    "ACCOUNT_DISABLED", "Dostęp do konta został wstrzymany.", 403
                )
            with self.auth.transaction() as auth_db:
                tokens = self.auth._issue(auth_db, row["user_id"])
                session = self.auth._lookup(auth_db, tokens["access_token"], "access")[
                    "session_id"
                ]
            db.execute(
                "INSERT INTO portal_browser_links VALUES (?,?)",
                (token_hash(cookie), session),
            )
        return tokens

    def logout_browser(self, cookie):
        if not isinstance(cookie, str) or not 32 <= len(cookie) <= 200:
            return
        self._logout_browser_hash(token_hash(cookie))

    def logout_access(self, access):
        try:
            with self.auth.transaction() as db:
                row = self.auth._lookup(db, access, "access")
                family = db.execute(
                    "SELECT family_id FROM session_lineage WHERE session_id=?",
                    (row["session_id"],),
                ).fetchone()
        except ValueError:
            return
        with self.store.transaction() as db:
            links = db.execute(
                "SELECT browser_hash FROM portal_browser_links WHERE auth_session=?",
                (family["family_id"] if family else row["session_id"],),
            ).fetchall()
        for link in links:
            self._logout_browser_hash(link["browser_hash"])
        try:
            self.auth.logout(access)
        except ValueError:
            pass

    def _logout_browser_hash(self, identity):
        with self.store.transaction() as db:
            links = db.execute(
                "SELECT auth_session FROM portal_browser_links WHERE browser_hash=?",
                (identity,),
            ).fetchall()
            db.execute(
                "UPDATE portal_browser_sessions SET revoked=1 WHERE hash=?",
                (identity,),
            )
            with self.auth.transaction() as auth_db:
                for row in links:
                    auth_db.execute(
                        """UPDATE sessions SET revoked=1 WHERE id IN (
                        SELECT session_id FROM session_lineage WHERE family_id=(
                            SELECT family_id FROM session_lineage WHERE session_id=?)) OR id=?""",
                        (row["auth_session"], row["auth_session"]),
                    )

    def search(
        self, query, operation, lookup, user_id=None, guest_cookie=None, ip_hash="local"
    ):
        request_hash = digest({"query": query})
        guest = (
            guest_cookie
            if isinstance(guest_cookie, str) and 32 <= len(guest_cookie) <= 200
            else secrets.token_urlsafe(32)
        )
        with self.store.transaction() as db:
            if user_id:
                row, previous = self._consume(
                    db, user_id, "lookup:" + operation, request_hash
                )
                if previous and previous["response"]:
                    return json.loads(previous["response"]), None
            else:
                identity = token_hash(guest)
                record = db.execute(
                    "SELECT * FROM portal_guests WHERE hash=?", (identity,)
                ).fetchone()
                if record and record["expires_at"] <= int(self.clock()):
                    db.execute("DELETE FROM portal_guests WHERE hash=?", (identity,))
                    db.execute(
                        "DELETE FROM portal_guest_requests WHERE guest_hash=?",
                        (identity,),
                    )
                    record = None
                previous = db.execute(
                    "SELECT * FROM portal_guest_requests WHERE guest_hash=? AND operation=?",
                    (identity, operation),
                ).fetchone()
                if previous:
                    if previous["request_hash"] != request_hash:
                        raise AccessDenied(
                            "IDEMPOTENCY_CONFLICT", "Ponów wyszukiwanie.", 409
                        )
                    return json.loads(previous["response"]), guest
                day = int(self.clock()) // 86400
                used_ip = db.execute(
                    "SELECT used FROM portal_limits WHERE scope='guest-day' AND identity=? AND bucket=?",
                    (ip_hash, day),
                ).fetchone()
                if (record and record["used"] >= 3) or (
                    used_ip and used_ip["used"] >= 3
                ):
                    raise AccessDenied(
                        "GUEST_QUOTA_EXHAUSTED",
                        "Wykorzystano 3 darmowe wyszukiwania. Zaloguj się lub utwórz konto.",
                    )
                db.execute(
                    "INSERT OR IGNORE INTO portal_guests VALUES (?,0,?)",
                    (identity, int(self.clock()) + 86400),
                )
            # lookup must be a local read; a failure rolls back the credit.
            items = lookup(query)
            if user_id:
                used = self._account(db, user_id)["used"]
                limit = PLANS[row["plan"]].searches
                result = {
                    "items": items,
                    "query": query,
                    "remaining": None if limit is None else max(0, limit - used),
                    "example": False,
                }
                db.execute(
                    "UPDATE portal_usage SET response=? WHERE user_id=? AND grant_id=? AND operation=?",
                    (
                        json.dumps(result, ensure_ascii=False),
                        user_id,
                        row["grant_id"],
                        "lookup:" + operation,
                    ),
                )
            else:
                db.execute(
                    "UPDATE portal_guests SET used=used+1 WHERE hash=?", (identity,)
                )
                db.execute(
                    """INSERT INTO portal_limits VALUES ('guest-day',?,?,1)
                    ON CONFLICT(scope,identity,bucket) DO UPDATE SET used=used+1""",
                    (ip_hash, day),
                )
                used = db.execute(
                    "SELECT used FROM portal_guests WHERE hash=?", (identity,)
                ).fetchone()[0]
                ip_used = db.execute(
                    "SELECT used FROM portal_limits WHERE scope='guest-day' AND identity=? AND bucket=?",
                    (ip_hash, day),
                ).fetchone()[0]
                result = {
                    "items": items,
                    "query": query,
                    "remaining": max(0, 3 - max(used, ip_used)),
                    "example": False,
                }
                db.execute(
                    "INSERT INTO portal_guest_requests VALUES (?,?,?,?)",
                    (
                        identity,
                        operation,
                        request_hash,
                        json.dumps(result, ensure_ascii=False),
                    ),
                )
        return result, guest if not user_id else None
