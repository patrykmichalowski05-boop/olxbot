import argparse
import os
import sqlite3
import unicodedata
from datetime import datetime, timedelta

import requests


DB_FILE = "/opt/olx-bot/watchlist.db"

STALE_DAYS = int(
    os.getenv(
        "WATCHLIST_STALE_DAYS",
        "7",
    )
)

HTTP_TIMEOUT = int(
    os.getenv(
        "WATCHLIST_HTTP_TIMEOUT",
        "15",
    )
)


UNAVAILABLE_MARKERS = [
    "ogloszenie nie jest juz dostepne",
    "to ogloszenie nie jest juz dostepne",
    "to ogloszenie jest juz nieaktualne",
    "ogloszenie jest nieaktualne",
    "oferta nie jest juz dostepna",
    "listing is no longer available",
]


def normalize(text):

    text = str(
        text or ""
    ).lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def ensure_column(
    conn,
    name,
    definition,
):

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(watchlist)"
        ).fetchall()
    }

    if name not in columns:

        conn.execute(
            f"""
            ALTER TABLE watchlist
            ADD COLUMN {name} {definition}
            """
        )


def init_db():

    conn = connect()

    # Na wypadek pustej/nowej bazy.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL UNIQUE,

            title TEXT,
            url TEXT,

            current_price REAL,

            max_buy REAL,
            opening REAL,

            score INTEGER,

            action TEXT,

            status TEXT NOT NULL
                DEFAULT 'WATCHING',

            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,

            triggered_at TEXT
        )
    """)

    ensure_column(
        conn,
        "last_checked",
        "TEXT",
    )

    ensure_column(
        conn,
        "http_status",
        "INTEGER",
    )

    ensure_column(
        conn,
        "close_reason",
        "TEXT",
    )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_watchlist_lifecycle_status
        ON watchlist(status)
    """)

    conn.commit()
    conn.close()


def parse_date(value):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            str(value)
        )

    except Exception:

        return None


def check_offer(
    session,
    url,
):

    if not url:

        return {
            "state": "UNKNOWN",
            "http_status": None,
            "reason": "NO_URL",
        }

    try:

        response = session.get(
            url,
            timeout=HTTP_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as e:

        return {
            "state": "UNKNOWN",
            "http_status": None,
            "reason": (
                "NETWORK_ERROR: "
                f"{type(e).__name__}"
            ),
        }

    status = (
        response.status_code
    )

    if status in [
        404,
        410,
    ]:

        return {
            "state": "CLOSED",
            "http_status": status,
            "reason": f"HTTP_{status}",
        }

    # Blokady OLX nie oznaczają,
    # że ogłoszenie zniknęło.
    if status in [
        403,
        429,
    ]:

        return {
            "state": "UNKNOWN",
            "http_status": status,
            "reason": f"HTTP_{status}",
        }

    if status >= 500:

        return {
            "state": "UNKNOWN",
            "http_status": status,
            "reason": f"HTTP_{status}",
        }

    body = normalize(
        response.text[:700000]
    )

    for marker in (
        UNAVAILABLE_MARKERS
    ):

        if marker in body:

            return {
                "state": "CLOSED",
                "http_status": status,
                "reason": (
                    "OLX_UNAVAILABLE"
                ),
            }

    if 200 <= status < 400:

        return {
            "state": "ACTIVE",
            "http_status": status,
            "reason": "OK",
        }

    return {
        "state": "UNKNOWN",
        "http_status": status,
        "reason": f"HTTP_{status}",
    }


def run(
    dry_run=False,
    limit=None,
):

    init_db()

    conn = connect()

    query = """
        SELECT *
        FROM watchlist

        WHERE status IN (
            'WATCHING',
            'TRIGGERED',
            'STALE'
        )

        ORDER BY
            CASE status
                WHEN 'TRIGGERED' THEN 1
                WHEN 'WATCHING' THEN 2
                WHEN 'STALE' THEN 3
                ELSE 4
            END,
            last_seen DESC
    """

    params = ()

    if limit:

        query += " LIMIT ?"
        params = (
            int(limit),
        )

    rows = conn.execute(
        query,
        params,
    ).fetchall()

    now = datetime.now()

    stale_cutoff = (
        now
        -
        timedelta(
            days=STALE_DAYS
        )
    )

    stats = {
        "checked": 0,
        "active": 0,
        "closed": 0,
        "stale": 0,
        "unknown": 0,
    }

    session = (
        requests.Session()
    )

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0 Safari/537.36"
        ),

        "Accept-Language":
            "pl-PL,pl;q=0.9,en;q=0.7",
    })


    for row in rows:

        stats[
            "checked"
        ] += 1

        result = check_offer(
            session,
            row["url"],
        )

        print()

        print(
            f"[WATCHLIST #{row['id']}] "
            f"{row['title']}"
        )

        print(
            f"STATUS: "
            f"{row['status']}"
        )

        print(
            f"HTTP: "
            f"{result['http_status']}"
        )

        print(
            f"CHECK: "
            f"{result['state']} | "
            f"{result['reason']}"
        )


        # ================================================
        # OFERTA ZNIKNĘŁA
        # ================================================

        if (
            result["state"]
            ==
            "CLOSED"
        ):

            stats[
                "closed"
            ] += 1

            if not dry_run:

                conn.execute("""
                    UPDATE watchlist

                    SET
                        status = 'CLOSED',
                        last_checked = ?,
                        http_status = ?,
                        close_reason = ?

                    WHERE id = ?
                """, (
                    now.isoformat(
                        timespec="seconds"
                    ),

                    result[
                        "http_status"
                    ],

                    result[
                        "reason"
                    ],

                    row["id"],
                ))

            print(
                "→ CLOSED"
            )

            continue


        # ================================================
        # NIEPEWNY CHECK
        # ================================================

        if (
            result["state"]
            ==
            "UNKNOWN"
        ):

            stats[
                "unknown"
            ] += 1

            if not dry_run:

                conn.execute("""
                    UPDATE watchlist

                    SET
                        last_checked = ?,
                        http_status = ?

                    WHERE id = ?
                """, (
                    now.isoformat(
                        timespec="seconds"
                    ),

                    result[
                        "http_status"
                    ],

                    row["id"],
                ))

            # NIE zamykamy przy 403,
            # timeoutach ani błędach OLX.
            print(
                "→ pozostaje bez zmian"
            )

            continue


        stats[
            "active"
        ] += 1


        # ================================================
        # STALE
        # ================================================

        last_seen = parse_date(
            row["last_seen"]
        )

        should_stale = (
            row["status"]
            ==
            "WATCHING"
            and
            last_seen is not None
            and
            last_seen
            <
            stale_cutoff
        )


        if should_stale:

            stats[
                "stale"
            ] += 1

            if not dry_run:

                conn.execute("""
                    UPDATE watchlist

                    SET
                        status = 'STALE',
                        last_checked = ?,
                        http_status = ?,
                        close_reason = 'NO_UPDATE_7D'

                    WHERE id = ?
                """, (
                    now.isoformat(
                        timespec="seconds"
                    ),

                    result[
                        "http_status"
                    ],

                    row["id"],
                ))

            print(
                "→ STALE"
            )

        else:

            if not dry_run:

                conn.execute("""
                    UPDATE watchlist

                    SET
                        last_checked = ?,
                        http_status = ?

                    WHERE id = ?
                """, (
                    now.isoformat(
                        timespec="seconds"
                    ),

                    result[
                        "http_status"
                    ],

                    row["id"],
                ))

            print(
                "→ ACTIVE"
            )


    if not dry_run:

        conn.commit()

    conn.close()

    print()
    print(
        "=" * 80
    )

    print(
        "WATCHLIST LIFECYCLE"
    )

    print(
        "=" * 80
    )

    for key, value in (
        stats.items()
    ):

        print(
            f"{key.upper():10}: "
            f"{value}"
        )

    if dry_run:

        print()
        print(
            "DRY RUN - baza nie została zmieniona."
        )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        limit=args.limit,
    )
