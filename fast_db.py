import sqlite3

from datetime import (
    datetime,
    timedelta,
)


DB_FILE = "/opt/olx-bot/fast.db"


# ============================================================
# TIME
# ============================================================

def now():

    return datetime.now().isoformat(
        timespec="seconds"
    )


# ============================================================
# DB
# ============================================================

def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = (
        sqlite3.Row
    )

    return conn


def init_db():

    with connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS fast_offers (

                offer_id TEXT PRIMARY KEY,

                title TEXT,
                url TEXT,

                first_price INTEGER,
                current_price INTEGER,
                lowest_price INTEGER,

                first_seen TEXT,
                last_seen TEXT,

                seen_count INTEGER DEFAULT 1,
                price_changes INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                offer_id TEXT NOT NULL,

                title TEXT,
                url TEXT,

                price INTEGER,

                mode TEXT,
                trigger TEXT,

                status TEXT DEFAULT 'PENDING',

                queued_at TEXT,
                updated_at TEXT,

                attempts INTEGER DEFAULT 0,

                last_error TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_queue_status
            ON queue(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_queue_offer
            ON queue(offer_id)
        """)


# ============================================================
# FAST OFFERS
# ============================================================

def count_offers():

    init_db()

    with connect() as conn:

        return conn.execute("""
            SELECT COUNT(*)
            FROM fast_offers
        """).fetchone()[0]


def observe_offer(
    offer_id,
    title,
    price,
    url,
):

    init_db()

    timestamp = now()

    with connect() as conn:

        old = conn.execute("""
            SELECT *
            FROM fast_offers
            WHERE offer_id = ?
        """, (
            offer_id,
        )).fetchone()

        # ====================================================
        # NOWA OFERTA
        # ====================================================

        if old is None:

            conn.execute("""
                INSERT INTO fast_offers (

                    offer_id,

                    title,
                    url,

                    first_price,
                    current_price,
                    lowest_price,

                    first_seen,
                    last_seen,

                    seen_count,
                    price_changes
                )
                VALUES (
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    1, 0
                )
            """, (
                offer_id,

                title,
                url,

                price,
                price,
                price,

                timestamp,
                timestamp,
            ))

            return {
                "new": True,
                "price_drop": False,
                "previous_price": None,
                "current_price": price,
            }

        # ====================================================
        # ISTNIEJĄCA
        # ====================================================

        old_price = (
            old["current_price"]
        )

        lowest = (
            old["lowest_price"]
        )

        price_changed = (
            price is not None
            and
            old_price is not None
            and
            price != old_price
        )

        price_drop = (
            price_changed
            and
            price < old_price
        )

        if (
            price is not None
            and
            (
                lowest is None
                or
                price < lowest
            )
        ):

            lowest = price

        conn.execute("""
            UPDATE fast_offers

            SET
                title = ?,
                url = ?,

                current_price =
                    COALESCE(
                        ?,
                        current_price
                    ),

                lowest_price = ?,

                last_seen = ?,

                seen_count =
                    seen_count + 1,

                price_changes =
                    price_changes + ?

            WHERE offer_id = ?
        """, (
            title,
            url,

            price,

            lowest,

            timestamp,

            1 if price_changed else 0,

            offer_id,
        ))

    return {
        "new": False,

        "price_drop":
            price_drop,

        "previous_price":
            old_price,

        "current_price":
            price,
    }


# ============================================================
# QUEUE — ADD
# ============================================================

def enqueue(
    offer_id,
    title,
    url,
    price,
    mode,
    trigger,
):

    init_db()

    timestamp = now()

    with connect() as conn:

        # Jeżeli oferta już czeka albo jest przetwarzana,
        # nie dokładamy duplikatu.

        existing = conn.execute("""
            SELECT id
            FROM queue

            WHERE
                offer_id = ?

                AND status IN (
                    'PENDING',
                    'PROCESSING'
                )

            ORDER BY id DESC

            LIMIT 1
        """, (
            offer_id,
        )).fetchone()

        if existing:

            return False

        conn.execute("""
            INSERT INTO queue (

                offer_id,

                title,
                url,

                price,

                mode,
                trigger,

                status,

                queued_at,
                updated_at,

                attempts,

                last_error
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                'PENDING',
                ?,
                ?,
                0,
                NULL
            )
        """, (
            offer_id,

            title,
            url,

            price,

            mode,
            trigger,

            timestamp,
            timestamp,
        ))

    return True


# ============================================================
# QUEUE — CLAIM
# ============================================================

def claim_next():

    """
    Pobiera jeden PENDING i atomowo ustawia PROCESSING.
    """

    init_db()

    timestamp = now()

    conn = connect()

    try:

        conn.execute(
            "BEGIN IMMEDIATE"
        )

        row = conn.execute("""
            SELECT *
            FROM queue

            WHERE status = 'PENDING'

            ORDER BY id ASC

            LIMIT 1
        """).fetchone()

        if row is None:

            conn.commit()

            return None

        conn.execute("""
            UPDATE queue

            SET
                status = 'PROCESSING',
                attempts = attempts + 1,
                updated_at = ?,
                last_error = NULL

            WHERE id = ?
        """, (
            timestamp,
            row["id"],
        ))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM queue
            WHERE id = ?
        """, (
            row["id"],
        )).fetchone()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# QUEUE — DONE
# ============================================================

def mark_done(
    job_id,
):

    timestamp = now()

    with connect() as conn:

        conn.execute("""
            UPDATE queue

            SET
                status = 'DONE',
                updated_at = ?,
                last_error = NULL

            WHERE id = ?
        """, (
            timestamp,
            job_id,
        ))


# ============================================================
# QUEUE — FAILED / RETRY
# ============================================================

def mark_failed(
    job_id,
    error,
    max_attempts=3,
):

    timestamp = now()

    with connect() as conn:

        row = conn.execute("""
            SELECT attempts
            FROM queue
            WHERE id = ?
        """, (
            job_id,
        )).fetchone()

        if row is None:

            return "MISSING"

        attempts = (
            row["attempts"]
            or 0
        )

        # Do 3 prób.
        if attempts < max_attempts:

            status = "PENDING"

        else:

            status = "FAILED"

        conn.execute("""
            UPDATE queue

            SET
                status = ?,
                updated_at = ?,
                last_error = ?

            WHERE id = ?
        """, (
            status,
            timestamp,
            str(error)[:1000],
            job_id,
        ))

    return status


# ============================================================
# QUEUE — STALE PROCESSING
# ============================================================

def recover_stale_processing(
    minutes=30,
):

    init_db()

    cutoff = (
        datetime.now()
        -
        timedelta(
            minutes=minutes
        )
    ).isoformat(
        timespec="seconds"
    )

    timestamp = now()

    with connect() as conn:

        result = conn.execute("""
            UPDATE queue

            SET
                status = 'PENDING',
                updated_at = ?,
                last_error =
                    'STALE_PROCESSING_RECOVERY'

            WHERE
                status = 'PROCESSING'

                AND updated_at < ?
        """, (
            timestamp,
            cutoff,
        ))

        return result.rowcount


# ============================================================
# QUEUE STATS
# ============================================================

def queue_stats():

    init_db()

    result = {}

    with connect() as conn:

        for status in [
            "PENDING",
            "PROCESSING",
            "DONE",
            "FAILED",
        ]:

            result[
                status.lower()
            ] = conn.execute("""
                SELECT COUNT(*)
                FROM queue
                WHERE status = ?
            """, (
                status,
            )).fetchone()[0]

    return result


# ============================================================
# RECENT
# ============================================================

def recent_queue(
    limit=20,
):

    init_db()

    with connect() as conn:

        return conn.execute("""
            SELECT *
            FROM queue

            ORDER BY id DESC

            LIMIT ?
        """, (
            limit,
        )).fetchall()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    init_db()

    print(
        "FAST offers:",
        count_offers()
    )

    print(
        "QUEUE:",
        queue_stats()
    )
