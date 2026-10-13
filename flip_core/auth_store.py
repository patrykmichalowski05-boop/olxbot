import argparse
import getpass
import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid

from contextlib import contextmanager
from pathlib import Path

ITERATIONS = 350000
ACCESS_SECONDS = 900
REFRESH_SECONDS = 14 * 86400


def token_hash(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


class AuthStore:

    def __init__(self, path):
        self.path = Path(path).resolve()

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(
            self.path,
            timeout=15,
            isolation_level=None,
        )

        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")

        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()

        except BaseException:
            db.rollback()
            raise

        finally:
            db.close()

    def init_db(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL,
                    digest BLOB NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL
                        REFERENCES users(id),
                    revoked INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS tokens (
                    hash TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                        REFERENCES sessions(id),
                    kind TEXT NOT NULL
                        CHECK(kind IN ('access','refresh')),
                    expires INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                tokens_session_idx
                ON tokens(session_id);
            """)

    def create_owner(self, username, password):
        if (
            not 3 <= len(username) <= 60
            or not username.isascii()
        ):
            raise ValueError("Nieprawidlowy login")

        if len(password) < 12:
            raise ValueError("Haslo minimum 12 znakow")

        salt = secrets.token_bytes(16)

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            ITERATIONS,
        )

        with self.transaction() as db:
            if db.execute(
                "SELECT 1 FROM users LIMIT 1"
            ).fetchone():
                raise ValueError(
                    "Konto wlasciciela juz istnieje"
                )

            user_id = str(uuid.uuid4())

            db.execute("""
                INSERT INTO users
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                username,
                salt,
                digest,
            ))

        return user_id

    def _issue(self, db, user_id):
        session_id = str(uuid.uuid4())
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        now = int(time.time())

        db.execute("""
            INSERT INTO sessions(id,user_id)
            VALUES (?,?)
        """, (
            session_id,
            user_id,
        ))

        db.executemany("""
            INSERT INTO tokens
            VALUES (?, ?, ?, ?)
        """, [
            (
                token_hash(access),
                session_id,
                "access",
                now + ACCESS_SECONDS,
            ),
            (
                token_hash(refresh),
                session_id,
                "refresh",
                now + REFRESH_SECONDS,
            ),
        ])

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": ACCESS_SECONDS,
        }

    def login(self, username, password):
        with self.transaction() as db:
            row = db.execute("""
                SELECT * FROM users
                WHERE username=?
            """, (username,)).fetchone()

            salt = row["salt"] if row else b"\x00" * 16
            expected = (
                row["digest"] if row
                else b"\x00" * 32
            )

            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt,
                ITERATIONS,
            )

            if not row or not hmac.compare_digest(
                actual, expected
            ):
                raise ValueError(
                    "Nieprawidlowe dane logowania"
                )

            return self._issue(db, row["id"])

    def _lookup(self, db, token, kind):
        if (
            not isinstance(token, str)
            or not 32 <= len(token) <= 256
        ):
            raise ValueError("Invalid token")

        row = db.execute("""
            SELECT
                s.id AS session_id,
                s.user_id,
                s.revoked,
                t.expires
            FROM tokens t
            JOIN sessions s
                ON s.id=t.session_id
            WHERE t.hash=?
              AND t.kind=?
        """, (
            token_hash(token),
            kind,
        )).fetchone()

        if (
            not row
            or row["revoked"]
            or row["expires"] <= time.time()
        ):
            raise ValueError("Invalid token")

        return row

    def verify_access(self, token):
        with self.transaction() as db:
            return self._lookup(
                db, token, "access"
            )["user_id"]

    def refresh(self, token):
        with self.transaction() as db:
            row = self._lookup(
                db, token, "refresh"
            )

            db.execute("""
                UPDATE sessions
                SET revoked=1
                WHERE id=?
            """, (row["session_id"],))

            return self._issue(
                db, row["user_id"]
            )

    def logout(self, token):
        with self.transaction() as db:
            row = self._lookup(
                db, token, "access"
            )

            db.execute("""
                UPDATE sessions
                SET revoked=1
                WHERE id=?
            """, (row["session_id"],))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--db", required=True)
    parser.add_argument("--create-owner", required=True)

    args = parser.parse_args()

    password = getpass.getpass(
        "Haslo (minimum 12 znakow): "
    )

    store = AuthStore(args.db)
    store.init_db()

    print(
        "USER_ID:",
        store.create_owner(
            args.create_owner,
            password,
        ),
    )
