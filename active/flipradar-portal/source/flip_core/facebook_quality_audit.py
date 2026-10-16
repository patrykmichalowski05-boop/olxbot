"""Read-only audit of Facebook scanner and Telegram alert history."""

import argparse
import json
import re
import sqlite3

from collections import Counter
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from .category_router import categorize
from .contracts import RawListing, SourceStatus


def _read_rows(path, table, mandatory):
    path = Path(path).resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    uri = path.as_uri() + "?mode=ro"

    with closing(sqlite3.connect(
        uri, uri=True, timeout=15
    )) as db:

        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")

        exists = db.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type=? AND name=?
            """,
            ("table", table),
        ).fetchone()

        if not exists:
            raise ValueError(
                "MISSING_TABLE_" + table
            )

        columns = {
            row["name"]
            for row in db.execute(
                f"PRAGMA table_info({table})"
            )
        }

        missing = mandatory - columns

        if missing:
            raise ValueError(
                "MISSING_COLUMNS_"
                + ",".join(sorted(missing))
            )

        records = [
            dict(row)
            for row in db.execute(
                f"SELECT * FROM {table}"
            )
        ]

    return records, columns


def _fb_url(url):
    try:
        parsed = urlsplit(str(url or ""))
        host = (parsed.hostname or "").lower()

        allowed = {
            "facebook.com",
            "www.facebook.com",
            "m.facebook.com",
            "web.facebook.com",
        }

        return (
            parsed.scheme in ("http", "https")
            and host in allowed
            and bool(re.search(
                r"/marketplace/item/\d+",
                parsed.path,
            ))
        )

    except ValueError:
        return False


def _category(row):
    listing = RawListing(
        platform="FACEBOOK",
        external_id=str(
            row.get("listing_id") or ""
        ),
        canonical_url=str(
            row.get("url") or ""
        ),
        title=str(
            row.get("title") or ""
        ),
        description="",
        price_minor=None,
        currency="UNKNOWN",
        status=SourceStatus.UNKNOWN,
        fetched_at="",
        parser_version="fb-quality-card-v1",
    )

    return categorize(listing).category


def inspect(face_db, alerts_db, *, unknown_limit=20):
    if (
        type(unknown_limit) is not int
        or not 0 <= unknown_limit <= 50
    ):
        raise ValueError(
            "INVALID_UNKNOWN_LIMIT"
        )

    rows, columns = _read_rows(
        face_db,
        "facebook_offers",
        {
            "listing_id",
            "url",
            "title",
            "price",
            "analyzed",
        },
    )

    history, history_columns = _read_rows(
        alerts_db,
        "alerts",
        {"id", "url"},
    )

    counters = Counter()
    categories = Counter()
    suspicious = Counter()

    unknown_examples = []
    profits = []
    last_seen_values = []

    for row in rows:
        counters["cards"] += 1

        analyzed = row.get("analyzed") == 1

        counters["analyzed_flag"] += int(
            analyzed
        )

        counters["pending_flag"] += int(
            not analyzed
        )

        counters["card_price_present"] += int(
            row.get("price") is not None
        )

        counters["marked_alert_sent"] += int(
            row.get("alert_sent") == 1
        )

        counters["last_profit_present"] += int(
            row.get("last_profit") is not None
        )

        counters["seen_multiple_times"] += int(
            (row.get("seen_count") or 0) > 1
        )

        profit = row.get("last_profit")

        if (
            profit is not None
            and type(profit) in (int, float)
        ):
            profits.append(profit)

        if row.get("last_seen"):
            last_seen_values.append(
                str(row["last_seen"])
            )

        category = _category(row)
        categories[category] += 1

        if (
            category == "UNKNOWN"
            and len(unknown_examples) < unknown_limit
        ):
            unknown_examples.append({
                "title": str(
                    row.get("title") or ""
                )[:160],
                "card_price_unverified": (
                    row.get("price")
                ),
                "analyzed_flag": analyzed,
            })

        if not _fb_url(row.get("url")):
            suspicious[
                "unexpected_facebook_url"
            ] += 1

    facebook_alerts = [
        row
        for row in history
        if _fb_url(row.get("url"))
    ]

    counters[
        "facebook_alerts_in_alert_history"
    ] = len(facebook_alerts)

    counters[
        "facebook_distinct_alert_urls"
    ] = len({
        row.get("url")
        for row in facebook_alerts
    })

    counters[
        "last_profit_ge_400_unverified"
    ] = sum(
        value >= 400
        for value in profits
    )

    counters[
        "last_profit_below_400_unverified"
    ] = sum(
        value < 400
        for value in profits
    )

    return {
        "facebook": dict(counters),

        "categories_from_card_titles":
            dict(categories),

        "unknown_title_samples":
            unknown_examples,

        "suspected_input_issues":
            dict(suspicious),

        "facebook_last_seen_max":
            max(last_seen_values, default=None),

        "alert_history_schema_has_trigger":
            "trigger" in history_columns,

        "facebook_schema_has_alert_sent":
            "alert_sent" in columns,

        "explanatory_notes": [
            (
                "analyzed=1 oznacza zakonczenie "
                "analizy, a nie wyslanie Telegrama"
            ),
            (
                "WATCH, SKIP i deduplikacja "
                "moga tlumic powiadomienia"
            ),
            (
                "Bez logow skanera nie mozna "
                "ustalic przyczyny kazdego odrzutu"
            ),
            (
                "Zapis alertu nie potwierdza "
                "doreczenia do telefonu"
            ),
        ],

        "history_complete": False,
        "prices_and_currency_verified": False,
        "telegram_delivery_proved": False,
        "production_writes": False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--facebook",
        required=True,
    )

    parser.add_argument(
        "--alerts",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    facebook = Path(
        args.facebook
    ).resolve()

    alerts = Path(
        args.alerts
    ).resolve()

    report = Path(
        args.report
    ).resolve()

    if facebook != Path(
        "/opt/olx-bot/facebook/facebook_seen.db"
    ).resolve():
        parser.error("Nieoczekiwana baza Facebook")

    if alerts != Path(
        "/opt/olx-bot/alert_history.db"
    ).resolve():
        parser.error("Nieoczekiwana baza alertow")

    if not report.is_relative_to(
        Path("/root/olx-shadow").resolve()
    ):
        parser.error(
            "Raport poza /root/olx-shadow"
        )

    result = inspect(
        facebook,
        alerts,
    )

    report.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    console = {
        key: value
        for key, value in result.items()
        if key != "unknown_title_samples"
    }

    print(json.dumps(
        console,
        ensure_ascii=False,
        indent=2,
    ))

    print("FULL_REPORT:", report)


if __name__ == "__main__":
    main()
