"""Replay legacy snapshots into isolated SQLite store."""

import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from .observations import ObservationStore
from .snapshot_bridge import (
    SnapshotBridgeError,
    normalize_snapshot,
)


def replay(source_path, output_path, limit=1000):
    source_path = Path(source_path).resolve()
    output_path = Path(output_path).resolve()

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    if (
        output_path == source_path
        or output_path.is_relative_to(
            Path("/opt/olx-bot").resolve()
        )
    ):
        raise ValueError("Zabroniona lokalizacja zapisu")

    store = ObservationStore(output_path)
    store.init_db()

    platforms = Counter()
    rejected = Counter()
    processed = 0
    accepted = 0
    cursor = 0

    uri = source_path.as_uri() + "?mode=ro"

    with closing(sqlite3.connect(
        uri,
        uri=True,
        timeout=20,
    )) as source:
        source.row_factory = sqlite3.Row

        while processed < limit:
            batch_size = min(
                200, limit - processed
            )

            rows = source.execute("""
                SELECT *
                FROM snapshots
                WHERE id > ?
                ORDER BY id
                LIMIT ?
            """, (
                cursor,
                batch_size,
            )).fetchall()

            if not rows:
                break

            for row in rows:
                cursor = row["id"]
                processed += 1

                try:
                    listing, payload, analysis = (
                        normalize_snapshot(row)
                    )

                    listing_key = (
                        listing.platform
                        + ":"
                        + listing.external_id
                    )

                    observation_id = store.observe(
                        listing_key,
                        payload,
                    )

                    store.value(
                        observation_id,
                        "legacy-replay-v1",
                        "legacy-original",
                        f"legacy:{row['id']}",
                        analysis,
                    )

                except SnapshotBridgeError as exc:
                    rejected[str(exc)] += 1
                    continue

                accepted += 1
                platforms[listing.platform] += 1

    return {
        "processed_snapshots": processed,
        "accepted_snapshots": accepted,
        "rejected_snapshots": sum(
            rejected.values()
        ),
        "by_platform": dict(platforms),
        "rejection_reasons": dict(rejected),
        "last_snapshot_id": cursor,
        "shadow_database": str(output_path),
        "production_writes": False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source", required=True
    )
    parser.add_argument(
        "--output", required=True
    )
    parser.add_argument(
        "--limit", type=int, default=1000
    )
    parser.add_argument(
        "--report", required=True
    )

    args = parser.parse_args()

    if not 1 <= args.limit <= 5000:
        parser.error("Limit musi wynosic 1-5000")

    output = Path(args.output).resolve()
    safe_root = Path("/root/olx-shadow").resolve()

    if not output.is_relative_to(safe_root):
        parser.error(
            "Shadow DB musi byc w /root/olx-shadow"
        )

    report = replay(
        args.source,
        output,
        args.limit,
    )

    Path(args.report).write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
