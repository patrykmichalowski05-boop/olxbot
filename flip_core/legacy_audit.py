"""Read-only audit of existing Flip Hunter databases."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .money import to_minor


def read_table(root, filename, table, warnings):
    path = Path(root) / filename

    if not path.is_file():
        warnings.append(f"Missing database: {filename}")
        return []

    with closing(sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=10,
    )) as db:
        db.row_factory = sqlite3.Row

        exists = db.execute("""
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name=?
        """, (table,)).fetchone()

        if not exists:
            warnings.append(f"Missing table: {filename}/{table}")
            return []

        return [
            dict(row)
            for row in db.execute(
                f"SELECT * FROM {table}"
            )
        ]


def audit_legacy(root):
    warnings = []

    flips = read_table(
        root, "flip_results.db", "flips", warnings
    )
    prep = read_table(
        root, "deal_crm.db", "sale_prep_costs", warnings
    )
    alerts = read_table(
        root, "alert_history.db", "alerts", warnings
    )

    alert_keys = {
        row["id"]: row.get("offer_key")
        for row in alerts
        if row.get("id") is not None
    }

    prep_by_key = {}

    for row in prep:
        key = row.get("offer_key") or alert_keys.get(
            row.get("alert_id")
        )

        if key:
            prep_by_key.setdefault(key, []).append(row)

    overlapping = []
    invalid = []
    unmapped = 0

    for flip in flips:
        alert_id = flip.get("alert_id")
        key = alert_keys.get(alert_id)

        try:
            extra_minor = to_minor(
                flip.get("extra_cost") or 0
            )
        except ValueError:
            invalid.append(f"flip:{flip.get('id')}")
            continue

        if key is None:
            unmapped += 1
            continue

        related = prep_by_key.get(key, [])

        if extra_minor > 0 and related:
            overlapping.append({
                "flip_id": flip.get("id"),
                "prep_cost_rows": len(related),
            })

    for row in prep:
        try:
            to_minor(row.get("cost"))
        except ValueError:
            invalid.append(f"prep:{row.get('id')}")

    return {
        "flips_count": len(flips),
        "prep_cost_rows": len(prep),
        "alerts_count": len(alerts),
        "unmapped_flips": unmapped,
        "potential_double_count": overlapping,
        "invalid_amounts": invalid,
        "warnings": warnings,
        "migration_safe_automatically": (
            not overlapping
            and not invalid
            and not warnings
            and unmapped == 0
        ),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = audit_legacy(args.root)

    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "flips": report["flips_count"],
        "cost_rows": report["prep_cost_rows"],
        "possible_overlaps": len(
            report["potential_double_count"]
        ),
        "unmapped": report["unmapped_flips"],
        "invalid": len(report["invalid_amounts"]),
        "warnings": report["warnings"],
        "automatic_migration_safe":
            report["migration_safe_automatically"],
    }, indent=2, ensure_ascii=False))
