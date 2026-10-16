import sqlite3
import json

from datetime import datetime


DB_FILE = "/opt/olx-bot/decision_log.db"


def now():

    return datetime.now().isoformat(
        timespec="seconds"
    )


def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def json_text(value):

    try:

        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    except:

        return str(value)


def init_decision_db():

    with connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                created_at TEXT,

                offer_id TEXT,
                url TEXT,
                mode TEXT,

                decision TEXT,
                reason TEXT,
                stage TEXT,

                title TEXT,

                purchase_price INTEGER,

                cpu TEXT,
                gpu TEXT,
                ram INTEGER,
                disks TEXT,

                quick_sale INTEGER,
                total_cost INTEGER,
                profit INTEGER,

                valuation_source TEXT,
                confidence TEXT,

                static_quick_sale INTEGER,

                exact_samples INTEGER,
                exact_quick_sale INTEGER,

                market_min INTEGER,
                market_p25 INTEGER,
                market_median INTEGER,
                market_p75 INTEGER,

                similar_samples INTEGER,
                similar_quick_sale INTEGER,
                similarity REAL,
                similar_p25 INTEGER,
                similar_median INTEGER,

                sanity_cap_applied INTEGER,
                sanity_cap INTEGER,
                quick_sale_before_cap INTEGER,

                ai_condition TEXT,
                ai_adjustment_percent REAL,
                ai_confidence REAL,
                ai_summary TEXT,

                ai_issues TEXT,
                ai_missing_info TEXT,

                spec_ai_used INTEGER,
                spec_ai_fields TEXT,

                raw_details TEXT,
                raw_valuation TEXT,

                neighbor_samples INTEGER,
                neighbor_exact_gpu_samples INTEGER,
                neighbor_gpu_samples INTEGER,
                neighbor_similarity REAL,
                neighbor_p25 INTEGER,
                neighbor_median INTEGER,
                neighbor_quick_raw INTEGER,
                neighbor_quick_protected INTEGER,
                neighbor_protected INTEGER DEFAULT 0
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(decisions)"
            ).fetchall()
        }

        migrations = {
            "neighbor_samples":
                "INTEGER",

            "neighbor_exact_gpu_samples":
                "INTEGER",

            "neighbor_gpu_samples":
                "INTEGER",

            "neighbor_similarity":
                "REAL",

            "neighbor_p25":
                "INTEGER",

            "neighbor_median":
                "INTEGER",

            "neighbor_quick_raw":
                "INTEGER",

            "neighbor_quick_protected":
                "INTEGER",

            "neighbor_protected":
                "INTEGER DEFAULT 0",
        }

        for column, definition in migrations.items():

            if column not in columns:

                conn.execute(
                    f"""
                    ALTER TABLE decisions
                    ADD COLUMN {column} {definition}
                    """
                )

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_decisions_created
            ON decisions(created_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_decisions_offer
            ON decisions(offer_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_decisions_decision
            ON decisions(decision)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_decisions_profit
            ON decisions(profit)
        """)


def log_decision(
    offer_id,
    details,
    valuation,
    mode,
    offer_url,
    decision,
    reason,
    stage
):

    init_decision_db()

    details = details or {}
    valuation = valuation or {}

    disks = (
        details.get("disks")
        or []
    )

    ai_issues = (
        valuation.get("ai_issues")
        or []
    )

    ai_missing = (
        valuation.get("ai_missing_info")
        or []
    )

    spec_fields = (
        details.get("_spec_ai_fields")
        or []
    )

    values = {

        "created_at":
            now(),

        "offer_id":
            offer_id,

        "url":
            offer_url,

        "mode":
            mode,

        "decision":
            decision,

        "reason":
            reason,

        "stage":
            stage,

        "title":
            details.get("title"),

        "purchase_price":
            details.get("price"),

        "cpu":
            details.get("cpu"),

        "gpu":
            details.get("gpu"),

        "ram":
            details.get("ram"),

        "disks":
            json_text(disks),

        "quick_sale":
            valuation.get("quick_sale"),

        "total_cost":
            valuation.get("total_cost"),

        "profit":
            valuation.get("profit"),

        "valuation_source":
            valuation.get("valuation_source"),

        "confidence":
            valuation.get("confidence"),

        "static_quick_sale":
            valuation.get("static_quick_sale"),

        "exact_samples":
            valuation.get(
                "exact_samples",
                valuation.get(
                    "market_samples"
                )
            ),

        "exact_quick_sale":
            valuation.get("exact_quick_sale"),

        "market_min":
            valuation.get("market_min"),

        "market_p25":
            valuation.get("market_p25"),

        "market_median":
            valuation.get("market_median"),

        "market_p75":
            valuation.get("market_p75"),

        "similar_samples":
            valuation.get("similar_samples"),

        "similar_quick_sale":
            valuation.get("similar_quick_sale"),

        "similarity":
            valuation.get("similarity"),

        "similar_p25":
            valuation.get("similar_p25"),

        "similar_median":
            valuation.get("similar_median"),

        "sanity_cap_applied":
            int(
                bool(
                    valuation.get(
                        "sanity_cap_applied"
                    )
                )
            ),

        "sanity_cap":
            valuation.get("sanity_cap"),

        "quick_sale_before_cap":
            valuation.get(
                "quick_sale_before_cap"
            ),

        "ai_condition":
            valuation.get("ai_condition"),

        "ai_adjustment_percent":
            valuation.get(
                "ai_adjustment_percent"
            ),

        "ai_confidence":
            valuation.get("ai_confidence"),

        "ai_summary":
            valuation.get("ai_summary"),

        "ai_issues":
            json_text(ai_issues),

        "ai_missing_info":
            json_text(ai_missing),

        "spec_ai_used":
            int(
                bool(
                    details.get(
                        "_spec_ai_used"
                    )
                )
            ),

        "spec_ai_fields":
            json_text(spec_fields),

        "raw_details":
            json_text(details),

        "raw_valuation":
            json_text(valuation),

        # ======================================
        # V3
        # ======================================

        "neighbor_samples":
            valuation.get(
                "neighbor_samples"
            ),

        "neighbor_exact_gpu_samples":
            valuation.get(
                "neighbor_exact_gpu_samples"
            ),

        "neighbor_gpu_samples":
            valuation.get(
                "neighbor_gpu_samples"
            ),

        "neighbor_similarity":
            valuation.get(
                "neighbor_similarity"
            ),

        "neighbor_p25":
            valuation.get(
                "neighbor_p25"
            ),

        "neighbor_median":
            valuation.get(
                "neighbor_median"
            ),

        "neighbor_quick_raw":
            valuation.get(
                "neighbor_quick_raw"
            ),

        "neighbor_quick_protected":
            valuation.get(
                "neighbor_quick_protected"
            ),

        "neighbor_protected":
            int(
                bool(
                    valuation.get(
                        "neighbor_protected"
                    )
                )
            ),
    }

    columns = ", ".join(
        values.keys()
    )

    placeholders = ", ".join(
        "?"
        for _ in values
    )

    with connect() as conn:

        conn.execute(
            f"""
            INSERT INTO decisions (
                {columns}
            )
            VALUES (
                {placeholders}
            )
            """,
            tuple(
                values.values()
            )
        )


def stats():

    init_decision_db()

    with connect() as conn:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
        """).fetchone()[0]

        accepted = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE decision = 'ACCEPT'
        """).fetchone()[0]

        rejected = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE decision = 'REJECT'
        """).fetchone()[0]

        errors = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE decision = 'ERROR'
        """).fetchone()[0]

        avg_profit = conn.execute("""
            SELECT AVG(profit)
            FROM decisions
            WHERE profit IS NOT NULL
        """).fetchone()[0]

    return {
        "total":
            total,

        "accepted":
            accepted,

        "rejected":
            rejected,

        "errors":
            errors,

        "avg_profit":
            (
                round(avg_profit)
                if avg_profit is not None
                else None
            )
    }


def recent(
    limit=20
):

    init_decision_db()

    with connect() as conn:

        return conn.execute("""
            SELECT
                created_at,
                offer_id,

                decision,
                stage,
                reason,

                purchase_price,

                cpu,
                gpu,

                quick_sale,
                profit,

                valuation_source,
                confidence,

                neighbor_samples,
                neighbor_gpu_samples,
                neighbor_similarity,
                neighbor_protected

            FROM decisions

            ORDER BY id DESC

            LIMIT ?
        """, (
            limit,
        )).fetchall()


if __name__ == "__main__":

    init_decision_db()

    print(
        "DECISION DB:",
        stats()
    )
