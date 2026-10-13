import json
import sqlite3
from datetime import datetime

from alert_dedupe import make_offer_key


DB_FILE = "/opt/olx-bot/offer_snapshots.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,

            price REAL,

            title TEXT,
            url TEXT,

            details_json TEXT,
            valuation_json TEXT,
            action_json TEXT,

            score INTEGER,
            mode TEXT,
            trigger TEXT,

            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_snapshots_offer
        ON snapshots(
            offer_key,
            created_at
        )
    """)

    conn.commit()
    conn.close()


def safe_json(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return "{}"


def save_snapshot(
    details,
    valuation,
    action,
    offer_url,
    score=None,
    mode=None,
):
    init_db()

    details = details or {}
    valuation = valuation or {}
    action = action or {}

    offer_key = make_offer_key(
        details,
        offer_url,
    )

    conn = connect()


    # STAGE1_SNAPSHOT_DEDUPE_V2
    # Porownujemy cala analize, a nie tylko cene.

    conn.execute("BEGIN IMMEDIATE")

    existing = conn.execute("""
        SELECT details_json, valuation_json,
               action_json, score, mode, trigger
        FROM snapshots
        WHERE offer_key=?
        ORDER BY id DESC
        LIMIT 1
    """, (offer_key,)).fetchone()

    if existing:
        try:
            same = (
                json.loads(existing["details_json"] or "{}")
                == json.loads(safe_json(details))
                and json.loads(existing["valuation_json"] or "{}")
                == json.loads(safe_json(valuation))
                and json.loads(existing["action_json"] or "{}")
                == json.loads(safe_json(action))
                and int(existing["score"] or 0)
                == int(score or 0)
                and str(existing["mode"] or "")
                == str(mode or "")
                and str(existing["trigger"] or "")
                == str(details.get("_trigger") or "")
            )
        except (ValueError, TypeError):
            same = False

        if same:
            conn.rollback()
            conn.close()
            return False

    conn.execute("""
        INSERT INTO snapshots (

            offer_key,
            price,

            title,
            url,

            details_json,
            valuation_json,
            action_json,

            score,
            mode,
            trigger,

            created_at
        )

        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
    """, (
        offer_key,
        details.get("price"),

        str(
            details.get("title")
            or ""
        ),

        str(
            offer_url
            or ""
        ),

        safe_json(details),
        safe_json(valuation),
        safe_json(action),

        int(score or 0),

        str(mode or ""),

        str(
            details.get("_trigger")
            or ""
        ),

        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()
    conn.close()

    print(
        "[SNAPSHOT] zapisano pełną analizę:",
        details.get("title"),
    )

    return True


def latest_for_offer_key(
    offer_key,
):
    init_db()

    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM snapshots

        WHERE offer_key = ?

        ORDER BY id DESC

        LIMIT 1
    """, (
        offer_key,
    )).fetchone()

    conn.close()

    return row
