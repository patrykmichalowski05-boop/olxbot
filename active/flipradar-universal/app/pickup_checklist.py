import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/deal_crm.db"


ITEMS = [
    {
        "key": "specs",
        "label": "CPU / GPU zgodne z ogłoszeniem",
    },
    {
        "key": "ram",
        "label": "RAM - pojemność i działanie",
    },
    {
        "key": "disks",
        "label": "Dyski - pojemność i wykrywanie",
    },
    {
        "key": "smart",
        "label": "SMART dysków",
    },
    {
        "key": "temps",
        "label": "Temperatury CPU / GPU",
    },
    {
        "key": "benchmark",
        "label": "Benchmark / brak artefaktów",
    },
    {
        "key": "psu",
        "label": "Model zasilacza zgodny",
    },
    {
        "key": "ports",
        "label": "USB / LAN / audio / obraz",
    },
    {
        "key": "noise",
        "label": "Brak niepokojących dźwięków",
    },
    {
        "key": "visual",
        "label": "Stan wizualny zgodny",
    },
]


VALID_STATUS = {
    "PENDING",
    "OK",
    "PROBLEM",
}


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pickup_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_key TEXT NOT NULL,
            item_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            note TEXT,
            updated_at TEXT NOT NULL,

            UNIQUE(
                offer_key,
                item_key
            )
        )
    """)

    conn.commit()
    conn.close()


def set_check(
    offer_key,
    item_key,
    status,
    note=None,
):
    init_db()

    status = str(status).upper()

    if status not in VALID_STATUS:
        raise ValueError(
            "Nieprawidłowy status"
        )

    valid_keys = {
        item["key"]
        for item in ITEMS
    }

    if item_key not in valid_keys:
        raise ValueError(
            "Nieprawidłowy element checklisty"
        )

    conn = connect()

    conn.execute("""
        INSERT INTO pickup_checks (
            offer_key,
            item_key,
            status,
            note,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(
            offer_key,
            item_key
        )

        DO UPDATE SET
            status = excluded.status,
            note = excluded.note,
            updated_at = excluded.updated_at
    """, (
        offer_key,
        item_key,
        status,
        note,
        datetime.now().isoformat(
            timespec="seconds"
        ),
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
        FROM pickup_checks
        WHERE offer_key = ?
    """, (
        offer_key,
    )).fetchall()

    conn.close()

    saved = {
        row["item_key"]: row
        for row in rows
    }

    result = []

    for item in ITEMS:

        row = saved.get(
            item["key"]
        )

        result.append({
            "key": item["key"],
            "label": item["label"],
            "status": (
                row["status"]
                if row
                else "PENDING"
            ),
            "note": (
                row["note"]
                if row
                else None
            ),
        })

    return result


def readiness(
    checklist,
):
    total = len(checklist)

    ok = sum(
        1
        for item in checklist
        if item["status"] == "OK"
    )

    problems = sum(
        1
        for item in checklist
        if item["status"] == "PROBLEM"
    )

    pending = (
        total
        - ok
        - problems
    )

    return {
        "total": total,
        "ok": ok,
        "problems": problems,
        "pending": pending,
        "ready": (
            total > 0
            and ok == total
            and problems == 0
        ),
    }
