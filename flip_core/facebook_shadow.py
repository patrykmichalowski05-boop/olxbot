"""Ingest card-only Facebook observations into isolated shadow DB."""

import argparse
import json
import sqlite3

from contextlib import closing
from pathlib import Path

from .facebook_cards import read_cards
from .observations import ObservationStore


def ingest(source_db, shadow_db, limit=5000):
    source = Path(source_db).resolve()
    target = Path(shadow_db).resolve()

    if target == source or target.is_relative_to(
        Path("/opt/olx-bot").resolve()
    ):
        raise ValueError(
            "Zabroniony katalog docelowy"
        )

    payloads, report = read_cards(source, limit)

    store = ObservationStore(target)
    store.init_db()

    for payload in payloads:
        store.observe(
            "FACEBOOK:" + payload["external_id"],
            payload,
        )

    with closing(sqlite3.connect(
        target.as_uri() + "?mode=ro",
        uri=True,
    )) as db:
        observations = db.execute("""
            SELECT COUNT(*)
            FROM listing_observations
        """).fetchone()[0]

    return {
        **report,
        "shadow_observations_total": observations,
        "shadow_database": str(target),
        "source_data_quality": "CARD_ONLY_UNVERIFIED",
        "telegram_sent": False,
        "production_scanners_modified": False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=5000)

    args = parser.parse_args()

    root = Path("/root/olx-shadow").resolve()

    output = Path(args.output).resolve()
    report_path = Path(args.report).resolve()

    if (
        not output.is_relative_to(root)
        or not report_path.is_relative_to(root)
    ):
        parser.error(
            "Output i report musza byc w /root/olx-shadow"
        )

    expected_source = Path(
        "/opt/olx-bot/facebook/facebook_seen.db"
    ).resolve()

    if Path(args.source).resolve() != expected_source:
        parser.error(
            "Dozwolona jest tylko produkcyjna baza "
            "facebook_seen.db w trybie odczytu"
        )

    result = ingest(
        args.source,
        args.output,
        args.limit,
    )

    report_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    ))

    print("REPORT:", report_path)


if __name__ == "__main__":
    main()
