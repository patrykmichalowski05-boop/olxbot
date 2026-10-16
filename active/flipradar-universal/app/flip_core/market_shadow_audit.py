"""Read-only market analysis against shadow observations."""

import argparse
import json
import sqlite3

from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .category_router import categorize
from .contracts import RawListing, SourceStatus
from .market_evidence import MarketEvidence


def audit(
    shadow_path,
    market_path,
    *,
    limit=1000,
):
    shadow = Path(
        shadow_path
    ).resolve()

    if (
        not shadow.is_file()
        or not 1 <= limit <= 10000
    ):
        raise ValueError(
            "Brak shadow DB lub zly limit"
        )

    evidence = MarketEvidence(
        market_path
    )

    summary = Counter()
    sample = []

    uri = shadow.as_uri() + "?mode=ro"

    with closing(
        sqlite3.connect(
            uri,
            uri=True,
            timeout=20,
        )
    ) as conn:

        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT payload_json
            FROM listing_observations
            ORDER BY id DESC
            LIMIT ?
        """, (
            limit,
        )).fetchall()

        for item in rows:
            try:
                payload = json.loads(
                    item["payload_json"]
                )

                status_value = payload.get(
                    "status",
                    "UNKNOWN",
                )

                if status_value in (
                    SourceStatus._value2member_map_
                ):
                    status = SourceStatus(
                        status_value
                    )
                else:
                    status = (
                        SourceStatus.UNKNOWN
                    )

                listing = RawListing(
                    platform=str(
                        payload.get(
                            "platform"
                        ) or "UNKNOWN"
                    ),
                    external_id=str(
                        payload.get(
                            "external_id"
                        ) or ""
                    ),
                    canonical_url=str(
                        payload.get(
                            "canonical_url"
                        ) or ""
                    ),
                    title=str(
                        payload.get(
                            "title"
                        ) or ""
                    ),
                    description=str(
                        payload.get(
                            "description"
                        ) or ""
                    ),
                    price_minor=payload.get(
                        "price_minor"
                    ),
                    currency=str(
                        payload.get(
                            "currency"
                        ) or ""
                    ),
                    status=status,
                    fetched_at="",
                    parser_version=(
                        "legacy-shadow"
                    ),
                )

                category = categorize(
                    listing,
                    hints=payload.get(
                        "attributes"
                    ),
                )

                result = evidence.estimate(
                    category,
                    target_price_minor=(
                        listing.price_minor
                    ),
                    target_url=(
                        listing.canonical_url
                    ),
                )

                summary[
                    result["status"]
                ] += 1

                if len(sample) < 20:
                    sample.append({
                        "listing_id":
                            listing.external_id,

                        "category":
                            category.category,

                        "status":
                            result["status"],

                        "decision":
                            result["decision"],

                        "comparables":
                            result[
                                "comparable_count"
                            ],

                        "asking_p25_minor":
                            result[
                                "asking_p25_minor"
                            ],

                        "illustrative_profit_minor":
                            result[
                                "illustrative_profit_minor"
                            ],
                    })

            except (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                OverflowError,
            ):
                summary[
                    "INVALID_OBSERVATION"
                ] += 1

    return {
        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "observations": len(rows),

        "market_offers_inspected":
            evidence.total_loaded,

        "market_candidates_accepted":
            len(evidence.rows),

        "market_rows_rejected":
            evidence.rejections,

        "results":
            dict(summary),

        "examples":
            sample,

        "price_source":
            "ACTIVE_OLX_LISTING_ASKS_NOT_SALES",

        "no_automatic_buy_or_telegram":
            True,

        "production_database_writes":
            False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--shadow",
        required=True,
    )

    parser.add_argument(
        "--market",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    safe = Path(
        "/root/olx-shadow"
    ).resolve()

    shadow = Path(
        args.shadow
    ).resolve()

    report = Path(
        args.report
    ).resolve()

    if (
        not shadow.is_relative_to(safe)
        or not report.is_relative_to(safe)
    ):
        parser.error(
            "Raport i baza shadow musza byc "
            "w /root/olx-shadow"
        )

    data = audit(
        shadow,
        args.market,
        limit=args.limit,
    )

    report.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    visible = {
        key: value
        for key, value in data.items()
        if key != "examples"
    }

    print(
        json.dumps(
            visible,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("REPORT:", report)


if __name__ == "__main__":
    main()
