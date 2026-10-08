import sys
import sqlite3
import json


DB_FILE = "/opt/olx-bot/decision_log.db"


def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def pretty_json(value):

    if not value:
        return "-"

    try:

        parsed = json.loads(
            value
        )

        return json.dumps(
            parsed,
            ensure_ascii=False,
            indent=2
        )

    except:

        return str(value)


def main():

    if len(sys.argv) < 2:

        print(
            "Użycie:"
        )

        print(
            "python decision_inspect.py ID_OLX"
        )

        return

    offer_id = (
        sys.argv[1]
    )

    with connect() as conn:

        rows = conn.execute("""
            SELECT *
            FROM decisions

            WHERE offer_id = ?

            ORDER BY id ASC
        """, (
            offer_id,
        )).fetchall()

    if not rows:

        print(
            "Brak decyzji dla:",
            offer_id
        )

        return

    for row in rows:

        print()
        print("=" * 90)

        print(
            row["created_at"]
        )

        print(
            f"DECISION: "
            f"{row['decision']}"
        )

        print(
            f"STAGE:    "
            f"{row['stage']}"
        )

        print(
            f"REASON:   "
            f"{row['reason']}"
        )

        print()
        print(
            f"Cena:      "
            f"{row['purchase_price']}"
        )

        print(
            f"CPU:       "
            f"{row['cpu']}"
        )

        print(
            f"GPU:       "
            f"{row['gpu']}"
        )

        print(
            f"RAM:       "
            f"{row['ram']}"
        )

        print()

        print(
            f"Quick sale: "
            f"{row['quick_sale']}"
        )

        print(
            f"Koszt:      "
            f"{row['total_cost']}"
        )

        print(
            f"Zysk:       "
            f"{row['profit']}"
        )

        print()

        print(
            f"Źródło: "
            f"{row['valuation_source']}"
        )

        print(
            f"Confidence: "
            f"{row['confidence']}"
        )

        print()

        print(
            f"Exact: "
            f"{row['exact_samples']} | "
            f"{row['exact_quick_sale']}"
        )

        print(
            f"Similar: "
            f"{row['similar_samples']} | "
            f"{row['similar_quick_sale']} | "
            f"{row['similarity']}%"
        )

        print(
            f"Static: "
            f"{row['static_quick_sale']}"
        )

        print()

        print(
            f"Sanity cap: "
            f"{row['sanity_cap_applied']}"
        )

        print(
            f"Cap: "
            f"{row['sanity_cap']}"
        )

        print()

        print(
            f"AI condition: "
            f"{row['ai_condition']}"
        )

        print(
            f"AI adjustment: "
            f"{row['ai_adjustment_percent']}%"
        )

        print(
            f"AI confidence: "
            f"{row['ai_confidence']}"
        )

        print()

        print(
            "AI issues:"
        )

        print(
            pretty_json(
                row[
                    "ai_issues"
                ]
            )
        )

        print()

        print(
            f"URL: "
            f"{row['url']}"
        )


if __name__ == "__main__":
    main()
