import math
import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/purchase_checklist.db"


ITEMS = [
    {
        "key": "psu",
        "label": "Model i moc zasilacza",
        "missing_penalty": 100,
        "problem_penalty": 250,
    },
    {
        "key": "gpu_temp",
        "label": "Temperatura GPU pod obciążeniem",
        "missing_penalty": 50,
        "problem_penalty": 200,
    },
    {
        "key": "cpu_temp",
        "label": "Temperatura CPU pod obciążeniem",
        "missing_penalty": 50,
        "problem_penalty": 150,
    },
    {
        "key": "smart",
        "label": "SMART dysku",
        "missing_penalty": 50,
        "problem_penalty": 200,
    },
    {
        "key": "benchmark",
        "label": "Benchmark / test GPU",
        "missing_penalty": 50,
        "problem_penalty": 250,
    },
    {
        "key": "inside_photo",
        "label": "Zdjęcie wnętrza komputera",
        "missing_penalty": 30,
        "problem_penalty": 100,
    },
    {
        "key": "serial",
        "label": "Numery seryjne / zgodność sprzętu",
        "missing_penalty": 30,
        "problem_penalty": 100,
    },
    {
        "key": "noise",
        "label": "Hałas / wentylatory / piszczenie",
        "missing_penalty": 30,
        "problem_penalty": 150,
    },
]


VALID_STATUS = {
    "UNKNOWN",
    "OK",
    "MISSING",
    "PROBLEM",
}


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS checks (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            item_key TEXT NOT NULL,

            status TEXT NOT NULL
                DEFAULT 'UNKNOWN',

            note TEXT,

            updated_at TEXT NOT NULL,

            UNIQUE(
                offer_key,
                item_key
            )
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_checks_offer
        ON checks(offer_key)
    """)

    conn.commit()
    conn.close()


def set_status(
    offer_key,
    item_key,
    status,
):
    init_db()

    status = str(
        status or ""
    ).upper()

    if status not in VALID_STATUS:
        raise ValueError(
            "Nieprawidłowy status checklisty."
        )

    valid_keys = {
        item["key"]
        for item in ITEMS
    }

    if item_key not in valid_keys:
        raise ValueError(
            "Nieprawidłowy element checklisty."
        )

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    conn = connect()

    conn.execute("""
        INSERT INTO checks (
            offer_key,
            item_key,
            status,
            updated_at
        )

        VALUES (?, ?, ?, ?)

        ON CONFLICT(
            offer_key,
            item_key
        )

        DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
    """, (
        offer_key,
        item_key,
        status,
        now,
    ))

    conn.commit()
    conn.close()


def get_checklist(
    offer_key,
):
    init_db()

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM checks
        WHERE offer_key = ?
    """, (
        offer_key,
    )).fetchall()

    conn.close()

    existing = {
        row["item_key"]:
            dict(row)
        for row in rows
    }

    result = []

    for config in ITEMS:

        saved = existing.get(
            config["key"],
            {},
        )

        item = dict(config)

        item["status"] = (
            saved.get(
                "status"
            )
            or
            "UNKNOWN"
        )

        item["note"] = (
            saved.get(
                "note"
            )
            or
            ""
        )

        result.append(
            item
        )

    return result


def floor_50(value):
    try:
        return int(
            math.floor(
                float(value)
                /
                50
            )
            *
            50
        )
    except Exception:
        return None


def calculate_adjustment(
    base_max_buy,
    current_price,
    checklist,
):
    try:
        base_max_buy = float(
            base_max_buy
        )
    except Exception:
        base_max_buy = None

    try:
        current_price = float(
            current_price
        )
    except Exception:
        current_price = None

    penalty = 0
    problems = []

    for item in checklist:

        status = item[
            "status"
        ]

        value = 0

        if status == "MISSING":

            value = item[
                "missing_penalty"
            ]

        elif status == "PROBLEM":

            value = item[
                "problem_penalty"
            ]

        if value:

            penalty += value

            problems.append({
                "label":
                    item["label"],

                "status":
                    status,

                "penalty":
                    value,
            })

    adjusted_max = None

    if base_max_buy is not None:

        adjusted_max = floor_50(
            max(
                0,
                base_max_buy
                -
                penalty,
            )
        )

    opening = None

    if (
        adjusted_max is not None
        and
        current_price is not None
    ):

        opening = floor_50(
            min(
                current_price * 0.90,
                adjusted_max * 0.90,
            )
        )

    checked = sum(
        1
        for item in checklist
        if item["status"]
        !=
        "UNKNOWN"
    )

    ok_count = sum(
        1
        for item in checklist
        if item["status"]
        ==
        "OK"
    )

    missing_count = sum(
        1
        for item in checklist
        if item["status"]
        ==
        "MISSING"
    )

    problem_count = sum(
        1
        for item in checklist
        if item["status"]
        ==
        "PROBLEM"
    )

    return {
        "penalty":
            penalty,

        "adjusted_max_buy":
            adjusted_max,

        "adjusted_opening":
            opening,

        "problems":
            problems,

        "checked":
            checked,

        "total":
            len(checklist),

        "ok_count":
            ok_count,

        "missing_count":
            missing_count,

        "problem_count":
            problem_count,
    }
