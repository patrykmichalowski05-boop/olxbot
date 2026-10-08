import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/olx.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def init_db():

    with connect() as conn:

        # Zachowujemy starą kolumnę "price",
        # żeby migracja istniejącej olx.db była prosta.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY,
                title TEXT,
                price INTEGER,
                url TEXT,
                first_seen TEXT
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(offers)"
            ).fetchall()
        }

        migrations = {
            "first_price":
                "INTEGER",

            "lowest_price":
                "INTEGER",

            "last_seen":
                "TEXT",

            "last_analyzed_price":
                "INTEGER",

            "alerted":
                "INTEGER DEFAULT 0",

            "last_alerted_price":
                "INTEGER",

            "analysis_failures":
                "INTEGER DEFAULT 0",

            "last_error":
                "TEXT",
        }

        for column, definition in migrations.items():

            if column not in columns:

                conn.execute(
                    f"""
                    ALTER TABLE offers
                    ADD COLUMN {column} {definition}
                    """
                )

        # Uzupełniamy stare rekordy.
        conn.execute("""
            UPDATE offers
            SET first_price = price
            WHERE first_price IS NULL
        """)

        conn.execute("""
            UPDATE offers
            SET lowest_price = price
            WHERE lowest_price IS NULL
        """)

        conn.execute("""
            UPDATE offers
            SET last_seen = first_seen
            WHERE last_seen IS NULL
        """)

        conn.execute("""
            UPDATE offers
            SET alerted = 0
            WHERE alerted IS NULL
        """)

        conn.execute("""
            UPDATE offers
            SET analysis_failures = 0
            WHERE analysis_failures IS NULL
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_offers_last_seen
            ON offers(last_seen)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_offers_price
            ON offers(price)
        """)


def get_offer(offer_id):

    with connect() as conn:

        return conn.execute("""
            SELECT *
            FROM offers
            WHERE id = ?
        """, (
            offer_id,
        )).fetchone()


def offer_exists(offer_id):

    return get_offer(
        offer_id
    ) is not None


def observe_offer(
    offer_id,
    title,
    price,
    url
):
    """
    Rejestruje pojawienie się oferty.

    Zwraca m.in.:
    - czy oferta jest nowa,
    - czy cena spadła,
    - czy trzeba przeanalizować ją ponownie.
    """

    timestamp = now()

    old = get_offer(
        offer_id
    )

    # ==========================================
    # NOWA OFERTA
    # ==========================================

    if old is None:

        with connect() as conn:

            conn.execute("""
                INSERT INTO offers (
                    id,
                    title,
                    price,
                    url,
                    first_seen,
                    first_price,
                    lowest_price,
                    last_seen,
                    alerted,
                    analysis_failures
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                offer_id,
                title,
                price,
                url,
                timestamp,
                price,
                price,
                timestamp
            ))

        return {
            "is_new": True,
            "price_drop": False,
            "previous_price": None,
            "current_price": price,
            "last_analyzed_price": None,
            "should_analyze": True,
            "reason": "NEW"
        }

    # ==========================================
    # STARA OFERTA
    # ==========================================

    previous_price = old["price"]

    price_drop = (
        price is not None
        and
        previous_price is not None
        and
        price < previous_price
    )

    lowest_price = old["lowest_price"]

    if price is not None:

        if (
            lowest_price is None
            or
            price < lowest_price
        ):
            lowest_price = price

    # Jeżeli cena spadła, pozwalamy również
    # ponownie próbować ofertę, której parser
    # wcześniej kilka razy nie odczytał.
    reset_failures = (
        0
        if price_drop
        else old["analysis_failures"]
    )

    with connect() as conn:

        conn.execute("""
            UPDATE offers
            SET
                title = ?,
                price = COALESCE(?, price),
                url = ?,
                lowest_price = ?,
                last_seen = ?,
                analysis_failures = ?
            WHERE id = ?
        """, (
            title,
            price,
            url,
            lowest_price,
            timestamp,
            reset_failures,
            offer_id
        ))

    last_analyzed_price = (
        old["last_analyzed_price"]
    )

    failures = (
        reset_failures or 0
    )

    # Nigdy nie była analizowana.
    if (
        last_analyzed_price is None
        and
        failures < 3
    ):

        return {
            "is_new": False,
            "price_drop": price_drop,
            "previous_price": previous_price,
            "current_price": price,
            "last_analyzed_price":
                last_analyzed_price,
            "should_analyze": True,
            "reason": "PENDING"
        }

    # Cena jest niższa niż podczas ostatniej
    # pełnej analizy -> analizujemy ponownie.
    if (
        price is not None
        and
        last_analyzed_price is not None
        and
        price < last_analyzed_price
    ):

        return {
            "is_new": False,
            "price_drop": True,
            "previous_price": previous_price,
            "current_price": price,
            "last_analyzed_price":
                last_analyzed_price,
            "should_analyze": True,
            "reason": "PRICE_DROP"
        }

    return {
        "is_new": False,
        "price_drop": price_drop,
        "previous_price": previous_price,
        "current_price": price,
        "last_analyzed_price":
            last_analyzed_price,
        "should_analyze": False,
        "reason": "UNCHANGED"
    }


def mark_analyzed(
    offer_id,
    analyzed_price,
    alerted=False
):

    timestamp = now()

    with connect() as conn:

        if alerted:

            conn.execute("""
                UPDATE offers
                SET
                    last_analyzed_price = ?,
                    alerted = 1,
                    last_alerted_price = ?,
                    analysis_failures = 0,
                    last_error = NULL,
                    last_seen = ?
                WHERE id = ?
            """, (
                analyzed_price,
                analyzed_price,
                timestamp,
                offer_id
            ))

        else:

            conn.execute("""
                UPDATE offers
                SET
                    last_analyzed_price = ?,
                    analysis_failures = 0,
                    last_error = NULL,
                    last_seen = ?
                WHERE id = ?
            """, (
                analyzed_price,
                timestamp,
                offer_id
            ))


def mark_analysis_failure(
    offer_id,
    error
):

    with connect() as conn:

        conn.execute("""
            UPDATE offers
            SET
                analysis_failures =
                    COALESCE(analysis_failures, 0) + 1,
                last_error = ?,
                last_seen = ?
            WHERE id = ?
        """, (
            str(error)[:1000],
            now(),
            offer_id
        ))


# ==============================================
# KOMPATYBILNOŚĆ ZE STARYM KODEM
# ==============================================

def save_offer(
    offer_id,
    title,
    price,
    url
):

    observation = observe_offer(
        offer_id,
        title,
        price,
        url
    )

    mark_analyzed(
        offer_id,
        price,
        alerted=False
    )

    return observation
