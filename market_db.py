import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/market.db"


def now():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_market_db():

    with connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_offers (
                offer_id TEXT PRIMARY KEY,

                title TEXT,
                url TEXT,

                price INTEGER,

                cpu TEXT,
                gpu TEXT,
                ram INTEGER,
                disks TEXT,

                shipping INTEGER DEFAULT 0,

                source_query TEXT,

                first_seen TEXT,
                last_seen TEXT,

                seen_count INTEGER DEFAULT 1
            )
        """)

        # ==================================================
        # MIGRACJE
        # ==================================================

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(market_offers)"
            ).fetchall()
        }

        migrations = {
            "first_price":
                "INTEGER",

            "lowest_price":
                "INTEGER",

            "highest_price":
                "INTEGER",

            "active":
                "INTEGER DEFAULT 1",

            "inactive_since":
                "TEXT",

            "last_verified":
                "TEXT",

            "verification_failures":
                "INTEGER DEFAULT 0",

            "last_verification_error":
                "TEXT",

            "price_changes":
                "INTEGER DEFAULT 0",
        }

        for column, definition in migrations.items():

            if column not in columns:

                conn.execute(
                    f"""
                    ALTER TABLE market_offers
                    ADD COLUMN {column} {definition}
                    """
                )

        # stare rekordy
        conn.execute("""
            UPDATE market_offers
            SET first_price = price
            WHERE first_price IS NULL
        """)

        conn.execute("""
            UPDATE market_offers
            SET lowest_price = price
            WHERE lowest_price IS NULL
        """)

        conn.execute("""
            UPDATE market_offers
            SET highest_price = price
            WHERE highest_price IS NULL
        """)

        conn.execute("""
            UPDATE market_offers
            SET active = 1
            WHERE active IS NULL
        """)

        conn.execute("""
            UPDATE market_offers
            SET verification_failures = 0
            WHERE verification_failures IS NULL
        """)

        conn.execute("""
            UPDATE market_offers
            SET price_changes = 0
            WHERE price_changes IS NULL
        """)

        # ==================================================
        # HISTORIA CEN
        # ==================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                offer_id TEXT,
                price INTEGER,
                seen_at TEXT,

                FOREIGN KEY (offer_id)
                REFERENCES market_offers(offer_id)
            )
        """)

        # ==================================================
        # HISTORIA STATUSU
        # ==================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                offer_id TEXT,

                status TEXT,

                changed_at TEXT,

                reason TEXT
            )
        """)

        # ==================================================
        # INDEKSY
        # ==================================================

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_market_cpu
            ON market_offers(cpu)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_market_gpu
            ON market_offers(gpu)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_market_active
            ON market_offers(active)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_market_last_seen
            ON market_offers(last_seen)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_price_history_offer
            ON price_history(offer_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_status_history_offer
            ON status_history(offer_id)
        """)


def get_offer(offer_id):

    with connect() as conn:

        return conn.execute("""
            SELECT *
            FROM market_offers
            WHERE offer_id = ?
        """, (
            offer_id,
        )).fetchone()


def add_status_history(
    offer_id,
    status,
    reason=None
):

    with connect() as conn:

        conn.execute("""
            INSERT INTO status_history (
                offer_id,
                status,
                changed_at,
                reason
            )
            VALUES (?, ?, ?, ?)
        """, (
            offer_id,
            status,
            now(),
            reason
        ))


def add_offer(
    offer_id,
    title,
    url,
    price,
    cpu,
    gpu,
    ram,
    disks,
    shipping,
    source_query
):

    timestamp = now()

    disks_text = (
        " | ".join(disks)
        if isinstance(disks, list)
        else disks
    )

    old = get_offer(
        offer_id
    )

    if old:

        return touch_offer(
            offer_id=offer_id,
            title=title,
            price=price,
            url=url,
            source_query=source_query,
            cpu=cpu,
            gpu=gpu,
            ram=ram,
            disks=disks,
            shipping=shipping
        )

    with connect() as conn:

        conn.execute("""
            INSERT INTO market_offers (
                offer_id,
                title,
                url,
                price,
                cpu,
                gpu,
                ram,
                disks,
                shipping,
                source_query,

                first_seen,
                last_seen,
                seen_count,

                first_price,
                lowest_price,
                highest_price,

                active,
                inactive_since,

                verification_failures,
                price_changes
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, 1,
                ?, ?, ?,
                1, NULL,
                0, 0
            )
        """, (
            offer_id,
            title,
            url,
            price,
            cpu,
            gpu,
            ram,
            disks_text,
            int(bool(shipping)),
            source_query,

            timestamp,
            timestamp,

            price,
            price,
            price
        ))

        if price is not None:

            conn.execute("""
                INSERT INTO price_history (
                    offer_id,
                    price,
                    seen_at
                )
                VALUES (?, ?, ?)
            """, (
                offer_id,
                price,
                timestamp
            ))

    add_status_history(
        offer_id,
        "ACTIVE",
        "FIRST_SEEN"
    )

    return "NEW"


def validate_market_specs_update(old, title, cpu, gpu, ram):
    from market_reference_quality import (
        reject_reason,
        is_placeholder_title,
    )

    safe_title = old["title"]

    if (
        isinstance(title, str)
        and title.strip()
        and not is_placeholder_title(title)
        and not title.strip().casefold().startswith(
            "ogłoszenia - sprzedam"
        )
    ):
        safe_title = title

    changed = (
        safe_title != old["title"]
        or cpu is not None
        or gpu is not None
        or ram is not None
    )

    if changed:
        candidate = {
            "title": safe_title,
            "cpu": cpu if cpu is not None else old["cpu"],
            "gpu": gpu if gpu is not None else old["gpu"],
            "ram": ram if ram is not None else old["ram"],
        }

        reason = reject_reason(candidate)

        blocked = {
            "GPU_MISMATCH",
            "RAM_MISMATCH",
            "MULTI_GPU_TITLE",
            "INTEGRATED_ONLY",
            "NO_DEDICATED_GPU",
            "GPU_MISMATCH_VEGA",
        }

        if reason in blocked:
            raise ValueError(
                "MARKET_WRITE_BLOCKED: "
                + reason
            )

    return safe_title


def touch_offer(
    offer_id,
    title,
    price,
    url,
    source_query,
    cpu=None,
    gpu=None,
    ram=None,
    disks=None,
    shipping=None
):

    old = get_offer(
        offer_id
    )

    if not old:
        return None

    title = validate_market_specs_update(
        old, title, cpu, gpu, ram
    )

    timestamp = now()

    old_price = old["price"]

    disks_text = None

    if disks:

        disks_text = (
            " | ".join(disks)
            if isinstance(disks, list)
            else str(disks)
        )

    lowest = old["lowest_price"]
    highest = old["highest_price"]

    price_changed = (
        price is not None
        and
        old_price is not None
        and
        price != old_price
    )

    if price is not None:

        if (
            lowest is None
            or
            price < lowest
        ):
            lowest = price

        if (
            highest is None
            or
            price > highest
        ):
            highest = price

    was_inactive = (
        old["active"] == 0
    )

    with connect() as conn:

        conn.execute("""
            UPDATE market_offers
            SET
                title = COALESCE(?, title),
                url = COALESCE(?, url),

                price = COALESCE(?, price),

                cpu = COALESCE(?, cpu),
                gpu = COALESCE(?, gpu),
                ram = COALESCE(?, ram),
                disks = COALESCE(?, disks),

                shipping =
                    COALESCE(?, shipping),

                source_query =
                    COALESCE(?, source_query),

                last_seen = ?,

                seen_count =
                    seen_count + 1,

                lowest_price = ?,
                highest_price = ?,

                active = 1,
                inactive_since = NULL,

                verification_failures = 0,
                last_verification_error = NULL,

                price_changes =
                    price_changes + ?
            WHERE offer_id = ?
        """, (
            title,
            url,
            price,

            cpu,
            gpu,
            ram,
            disks_text,

            (
                int(bool(shipping))
                if shipping is not None
                else None
            ),

            source_query,

            timestamp,

            lowest,
            highest,

            1 if price_changed else 0,

            offer_id
        ))

        if price_changed:

            conn.execute("""
                INSERT INTO price_history (
                    offer_id,
                    price,
                    seen_at
                )
                VALUES (?, ?, ?)
            """, (
                offer_id,
                price,
                timestamp
            ))

    if price_changed:

        print(
            f"[MARKET PRICE] "
            f"{offer_id}: "
            f"{old_price} -> {price}"
        )

    if was_inactive:

        add_status_history(
            offer_id,
            "ACTIVE",
            "OFFER_REAPPEARED"
        )

    return (
        "PRICE_CHANGED"
        if price_changed
        else "SEEN"
    )


def mark_verified_active(
    offer_id
):

    old = get_offer(
        offer_id
    )

    if not old:
        return

    timestamp = now()

    was_inactive = (
        old["active"] == 0
    )

    with connect() as conn:

        conn.execute("""
            UPDATE market_offers
            SET
                active = 1,
                inactive_since = NULL,
                last_verified = ?,
                verification_failures = 0,
                last_verification_error = NULL
            WHERE offer_id = ?
        """, (
            timestamp,
            offer_id
        ))

    if was_inactive:

        add_status_history(
            offer_id,
            "ACTIVE",
            "URL_VERIFIED_AGAIN"
        )


def mark_verified_inactive(
    offer_id,
    reason
):

    old = get_offer(
        offer_id
    )

    if not old:
        return

    # Już oznaczona jako nieaktywna.
    if old["active"] == 0:

        with connect() as conn:

            conn.execute("""
                UPDATE market_offers
                SET last_verified = ?
                WHERE offer_id = ?
            """, (
                now(),
                offer_id
            ))

        return

    timestamp = now()

    with connect() as conn:

        conn.execute("""
            UPDATE market_offers
            SET
                active = 0,
                inactive_since = ?,
                last_verified = ?,
                verification_failures = 0,
                last_verification_error = NULL
            WHERE offer_id = ?
        """, (
            timestamp,
            timestamp,
            offer_id
        ))

    add_status_history(
        offer_id,
        "INACTIVE",
        reason
    )


def mark_verification_failure(
    offer_id,
    error
):

    with connect() as conn:

        conn.execute("""
            UPDATE market_offers
            SET
                last_verified = ?,

                verification_failures =
                    COALESCE(
                        verification_failures,
                        0
                    ) + 1,

                last_verification_error = ?
            WHERE offer_id = ?
        """, (
            now(),
            str(error)[:1000],
            offer_id
        ))


def get_stale_active_offers(
    stale_before,
    limit=30
):

    with connect() as conn:

        return conn.execute("""
            SELECT *
            FROM market_offers
            WHERE active = 1
            AND last_seen < ?
            ORDER BY last_seen ASC
            LIMIT ?
        """, (
            stale_before,
            limit
        )).fetchall()


def stats():

    with connect() as conn:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM market_offers
        """).fetchone()[0]

        active = conn.execute("""
            SELECT COUNT(*)
            FROM market_offers
            WHERE active = 1
        """).fetchone()[0]

        inactive = conn.execute("""
            SELECT COUNT(*)
            FROM market_offers
            WHERE active = 0
        """).fetchone()[0]

        price_changes = conn.execute("""
            SELECT
                COALESCE(
                    SUM(price_changes),
                    0
                )
            FROM market_offers
        """).fetchone()[0]

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "price_changes": price_changes
        }


def life_stats():

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                offer_id,
                first_seen,
                inactive_since,
                first_price,
                lowest_price,
                cpu,
                gpu
            FROM market_offers
            WHERE active = 0
            AND inactive_since IS NOT NULL
        """).fetchall()

    return rows
