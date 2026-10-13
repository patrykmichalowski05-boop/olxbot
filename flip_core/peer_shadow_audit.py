"""Read-only review ranking over historical shadow observations."""

import argparse
import json
import sqlite3

from collections import Counter
from contextlib import closing
from pathlib import Path

from .category_router import categorize
from .contracts import RawListing, SourceStatus
from .market_evidence import MarketEvidence
from .peer_market import review_offer


def audit(
    shadow_db,
    market_db,
    limit=1000,
):
    shadow_db = Path(shadow_db).resolve()

    if (
        not shadow_db.is_file()
        or not 1 <= limit <= 10000
    ):
        raise ValueError(
            "Nieprawidlowa baza shadow lub limit"
        )

    market = MarketEvidence(market_db)
    results = Counter()
    ranking = []

    with closing(
        sqlite3.connect(
            shadow_db.as_uri() + "?mode=ro",
            uri=True,
        )
    ) as db:
        rows = db.execute("""
            SELECT payload_json
            FROM listing_observations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    for (raw,) in rows:
        try:
            payload = json.loads(raw)

            if not isinstance(payload, dict):
                raise ValueError(
                    "Nieprawidlowy payload"
                )

            state = str(
                payload.get(
                    "status",
                    "UNKNOWN",
                )
            )

            listing = RawListing(
                platform=str(
                    payload.get("platform", "")
                ),
                external_id=str(
                    payload.get("external_id", "")
                ),
                canonical_url=str(
                    payload.get("canonical_url", "")
                ),
                title=str(
                    payload.get("title", "")
                ),
                description=str(
                    payload.get("description", "")
                ),
                price_minor=payload.get(
                    "price_minor"
                ),
                currency=str(
                    payload.get("currency", "")
                ),
                status=(
                    SourceStatus(state)
                    if state in SourceStatus._value2member_map_
                    else SourceStatus.UNKNOWN
                ),
                fetched_at="",
                parser_version="shadow-v1",
            )

            category = categorize(
                listing,
                hints=payload.get(
                    "attributes"
                ),
            )

            score = review_offer(
                market,
                category,
                listing.price_minor,
                listing.canonical_url,
                listing.status.value,
            )

            results[score["status"]] += 1

            if score["status"] == "SCENARIO_REVIEW_ONLY":
                ranking.append({
                    "platform": listing.platform,
                    "listing_id": listing.external_id,
                    "title": listing.title[:120],
                    "url": listing.canonical_url,
                    "price_minor": listing.price_minor,
                    "peer_count": score["peer_count"],
                    "scenario_profit_minor": score[
                        "scenario_profit_minor"
                    ],
                    "review_priority": score[
                        "review_priority"
                    ],
                    "decision": "REVIEW",
                })

        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
        ):
            results["INVALID_OBSERVATION"] += 1

    ranking.sort(
        key=lambda x: x[
            "scenario_profit_minor"
        ],
        reverse=True,
    )

    return {
        "inspected": len(rows),
        "market_candidates": len(
            market.rows
        ),
        "results": dict(results),
        "review_ranking": ranking[:20],
        "automatic_buy_allowed": False,
        "writes_to_production": False,
        "source_warning": (
            "OLX asking prices, not executed sales. "
            "Costs may be incomplete."
        ),
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

    args = parser.parse_args()

    root = Path(
        "/root/olx-shadow"
    ).resolve()

    shadow = Path(
        args.shadow
    ).resolve()

    report = Path(
        args.report
    ).resolve()

    if (
        not shadow.is_relative_to(root)
        or not report.is_relative_to(root)
    ):
        parser.error(
            "shadow i report musza byc "
            "w /root/olx-shadow"
        )

    result = audit(
        shadow,
        args.market,
    )

    report.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(
        {
            key: value
            for key, value in result.items()
            if key != "review_ranking"
        },
        indent=2,
        ensure_ascii=False,
    ))

    print(
        "REVIEW_RANKING_COUNT:",
        len(result["review_ranking"]),
    )

    print("REPORT:", report)


if __name__ == "__main__":
    main()
