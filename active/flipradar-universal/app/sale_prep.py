import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/deal_crm.db"
FLIP_DB = "/opt/olx-bot/flip_results.db"


KINDS = {
    "SSD",
    "RAM",
    "CASE",
    "PASTE",
    "CLEANING",
    "REPAIR",
    "OTHER",
}


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sale_prep_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            alert_id INTEGER,

            kind TEXT NOT NULL,
            cost REAL NOT NULL,

            note TEXT,

            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sale_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL UNIQUE,
            alert_id INTEGER,

            target_price REAL,
            minimum_price REAL,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_cost(
    offer_key,
    alert_id,
    kind,
    cost,
    note=None,
):
    init_db()

    kind = str(kind).upper()

    if kind not in KINDS:
        raise ValueError(
            "Nieprawidłowy rodzaj kosztu"
        )

    cost = float(cost)

    if cost < 0:
        raise ValueError(
            "Koszt nie może być ujemny"
        )

    conn = connect()

    conn.execute("""
        INSERT INTO sale_prep_costs (
            offer_key,
            alert_id,
            kind,
            cost,
            note,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        offer_key,
        alert_id,
        kind,
        cost,
        note,
        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()
    conn.close()


def delete_cost(cost_id):
    init_db()

    conn = connect()

    conn.execute("""
        DELETE FROM sale_prep_costs
        WHERE id = ?
    """, (
        cost_id,
    ))

    conn.commit()
    conn.close()


def save_plan(
    offer_key,
    alert_id,
    target_price,
    minimum_price,
):
    init_db()

    target_price = float(target_price)
    minimum_price = float(minimum_price)

    if target_price <= 0:
        raise ValueError(
            "Cena wystawienia musi być większa od 0"
        )

    if minimum_price <= 0:
        raise ValueError(
            "Cena minimalna musi być większa od 0"
        )

    if minimum_price > target_price:
        raise ValueError(
            "Cena minimalna nie może być większa od ceny wystawienia"
        )

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    conn = connect()

    conn.execute("""
        INSERT INTO sale_plans (
            offer_key,
            alert_id,
            target_price,
            minimum_price,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(offer_key)

        DO UPDATE SET
            alert_id = excluded.alert_id,
            target_price = excluded.target_price,
            minimum_price = excluded.minimum_price,
            updated_at = excluded.updated_at
    """, (
        offer_key,
        alert_id,
        target_price,
        minimum_price,
        now,
        now,
    ))

    conn.commit()
    conn.close()


def _purchase_data(alert_id):
    conn = sqlite3.connect(FLIP_DB)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute("""
            SELECT
                purchase_price,
                extra_cost

            FROM flips

            WHERE alert_id = ?

            ORDER BY id DESC

            LIMIT 1
        """, (
            alert_id,
        )).fetchone()

    except sqlite3.Error:
        row = None

    conn.close()

    if not row:
        return {
            "purchase_price": 0,
            "purchase_extra": 0,
        }

    return {
        "purchase_price":
            float(row["purchase_price"] or 0),

        "purchase_extra":
            float(row["extra_cost"] or 0),
    }


def summary(
    offer_key,
    alert_id,
    fallback_target=None,
):
    init_db()

    conn = connect()

    costs = conn.execute("""
        SELECT *
        FROM sale_prep_costs

        WHERE offer_key = ?

        ORDER BY
            created_at DESC,
            id DESC
    """, (
        offer_key,
    )).fetchall()

    plan = conn.execute("""
        SELECT *
        FROM sale_plans

        WHERE offer_key = ?
    """, (
        offer_key,
    )).fetchone()

    conn.close()

    purchase = _purchase_data(
        alert_id
    )

    prep_cost = sum(
        float(row["cost"] or 0)
        for row in costs
    )

    total_investment = (
        purchase["purchase_price"]
        + purchase["purchase_extra"]
        + prep_cost
    )

    if plan:
        target_price = plan[
            "target_price"
        ]

        minimum_price = plan[
            "minimum_price"
        ]

    else:
        target_price = (
            float(fallback_target)
            if fallback_target
            else None
        )

        minimum_price = None

    projected_profit = (
        float(target_price)
        - total_investment
        if target_price is not None
        else None
    )

    minimum_profit = (
        float(minimum_price)
        - total_investment
        if minimum_price is not None
        else None
    )

    return {
        "costs": costs,

        "purchase_price":
            purchase["purchase_price"],

        "purchase_extra":
            purchase["purchase_extra"],

        "prep_cost":
            prep_cost,

        "total_investment":
            total_investment,

        "target_price":
            target_price,

        "minimum_price":
            minimum_price,

        "projected_profit":
            projected_profit,

        "minimum_profit":
            minimum_profit,

        "has_plan":
            plan is not None,
    }
