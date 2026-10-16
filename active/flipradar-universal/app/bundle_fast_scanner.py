import os
import re
import sqlite3
import time

from datetime import datetime
from urllib.parse import quote, urljoin

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from browser_utils import (
    block_heavy_resources,
)

from bundle_detector import (
    analyze_bundle,
)

from fast_db import (
    enqueue,
)


DB_FILE = "/opt/olx-bot/fast.db"

BASE_URL = (
    "https://www.olx.pl/elektronika/"
    "komputery/komputery-stacjonarne/"
)


# ============================================================
# SEARCHES
# ============================================================

SEARCHES = [
    "setup gamingowy",
    "kompletny setup",
    "mega setup",
    "kompletny zestaw komputerowy",
    "komputer monitor",
    "pc monitor",
    "komputer simracing",
    "pc simracing",
    "komputer t300",
    "pc t300",
    "komputer kierownica",
    "pc kierownica",
    "komputer hotas",
    "pc hotas",
    "komputer vr",
    "pc vr",
]


QUERY_LIMIT = int(
    os.getenv(
        "BUNDLE_QUERY_LIMIT",
        str(len(SEARCHES)),
    )
)


MAX_CARDS_PER_QUERY = int(
    os.getenv(
        "BUNDLE_MAX_CARDS_PER_QUERY",
        "40",
    )
)


MAX_QUEUE_PER_RUN = int(
    os.getenv(
        "BUNDLE_MAX_QUEUE_PER_RUN",
        "15",
    )
)


# ============================================================
# DB
# ============================================================

def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def now():

    return datetime.now().isoformat(
        timespec="seconds"
    )


def init_bundle_db():

    with connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bundle_search_seen (

                offer_id TEXT PRIMARY KEY,

                title TEXT,
                url TEXT,

                first_price INTEGER,
                last_price INTEGER,

                query TEXT,

                first_seen TEXT,
                last_seen TEXT,

                seen_count INTEGER DEFAULT 1,
                queued_count INTEGER DEFAULT 0,

                last_trigger TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_bundle_seen_last
            ON bundle_search_seen(last_seen)
        """)


# ============================================================
# URL
# ============================================================

def make_url(query):

    return (
        BASE_URL
        + "?q="
        + quote(query)
        + "&search%5Border%5D=created_at:desc"
    )


def clean_url(url):

    if not url:
        return None

    return url.split("?")[0]


def get_offer_id(url):

    if not url:
        return None

    match = re.search(
        r"-CID\d+-(ID[a-zA-Z0-9]+)\.html",
        url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    matches = re.findall(
        r"ID[a-zA-Z0-9]+",
        url,
        re.IGNORECASE,
    )

    matches = [
        value
        for value in matches
        if value.upper() != "ID99"
    ]

    if not matches:
        return None

    return matches[-1]


def get_offer_link(card):

    links = card.locator(
        'a[href*="/d/oferta/"]'
    )

    for i in range(
        links.count()
    ):

        try:

            href = (
                links.nth(i)
                .get_attribute("href")
            )

        except Exception:
            continue

        if (
            href
            and "/d/oferta/" in href
            and "ID" in href
        ):

            return clean_url(
                urljoin(
                    "https://www.olx.pl",
                    href,
                )
            )

    return None


# ============================================================
# PRICE
# ============================================================

def parse_price(text):

    if not text:
        return None

    match = re.search(
        r"(\d[\d\s]*(?:[,.]\d{2})?)\s*zł",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    value = (
        match.group(1)
        .replace(" ", "")
        .replace(",", ".")
    )

    try:

        price = int(
            float(value)
        )

    except Exception:
        return None

    if price <= 0:
        return None

    return price


# ============================================================
# TITLE FILTER
# ============================================================

def looks_interesting(title):

    text = str(
        title or ""
    ).lower()

    bundle = analyze_bundle({
        "title": title,
        "description": "",
    })

    # Bundle Detector już jest pewny.
    if bundle.get(
        "is_bundle"
    ):

        return True

    pc_markers = [
        "komputer",
        " pc ",
        "pc ",
        " pc",
        "gaming",
        "rtx",
        "gtx",
        "radeon",
        "ryzen",
        "i5",
        "i7",
        "i9",
    ]

    bundle_markers = [
        "setup",
        "monitor",
        "simracing",
        "sim racing",
        "t300",
        "th8a",
        "hotas",
        "kierownica",
        "vr",
        "biurko",
    ]

    pc_score = sum(
        1
        for marker in pc_markers
        if marker in text
    )

    bundle_score = sum(
        1
        for marker in bundle_markers
        if marker in text
    )

    # "Mega setup RTX 4070..."
    if (
        "setup" in text
        and pc_score >= 1
    ):

        return True

    # PC + co najmniej dwa elementy dodatkowe.
    if (
        pc_score >= 1
        and bundle_score >= 2
    ):

        return True

    return False


# ============================================================
# OBSERVE BUNDLE
# ============================================================

def observe_bundle(
    offer_id,
    title,
    url,
    price,
    query,
):

    timestamp = now()

    with connect() as conn:

        old = conn.execute("""
            SELECT *
            FROM bundle_search_seen
            WHERE offer_id = ?
        """, (
            offer_id,
        )).fetchone()

        # ----------------------------------------------------
        # PIERWSZE WYKRYCIE
        # ----------------------------------------------------

        if old is None:

            conn.execute("""
                INSERT INTO bundle_search_seen (

                    offer_id,

                    title,
                    url,

                    first_price,
                    last_price,

                    query,

                    first_seen,
                    last_seen,

                    seen_count,
                    queued_count,

                    last_trigger
                )
                VALUES (
                    ?, ?, ?,
                    ?, ?,
                    ?,
                    ?, ?,
                    1,
                    0,
                    NULL
                )
            """, (

                offer_id,

                title,
                url,

                price,
                price,

                query,

                timestamp,
                timestamp,
            ))

            return {
                "should_queue": True,
                "trigger": "BUNDLE_DISCOVERY",
                "previous_price": None,
            }

        old_price = (
            old["last_price"]
        )

        price_drop = (
            price is not None
            and
            old_price is not None
            and
            price < old_price
        )

        conn.execute("""
            UPDATE bundle_search_seen

            SET
                title = ?,
                url = ?,
                last_price =
                    COALESCE(
                        ?,
                        last_price
                    ),

                query = ?,
                last_seen = ?,

                seen_count =
                    seen_count + 1

            WHERE offer_id = ?
        """, (
            title,
            url,
            price,
            query,
            timestamp,
            offer_id,
        ))

        if price_drop:

            return {
                "should_queue": True,
                "trigger": "BUNDLE_PRICE_DROP",
                "previous_price": old_price,
            }

        return {
            "should_queue": False,
            "trigger": None,
            "previous_price": old_price,
        }


def mark_bundle_queued(
    offer_id,
    trigger,
):

    with connect() as conn:

        conn.execute("""
            UPDATE bundle_search_seen

            SET
                queued_count =
                    queued_count + 1,

                last_trigger = ?

            WHERE offer_id = ?
        """, (
            trigger,
            offer_id,
        ))


# ============================================================
# MAIN
# ============================================================

def main():

    init_bundle_db()

    counters = {
        "queries": 0,
        "cards": 0,
        "duplicates_run": 0,
        "interesting": 0,
        "new_bundle": 0,
        "price_drop": 0,
        "queued": 0,
        "queue_limit": 0,
        "timeouts": 0,
    }

    processed_ids = set()

    start = time.time()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 720,
            },

            locale="pl-PL",

            service_workers="block",
        )

        block_heavy_resources(
            context
        )

        page = context.new_page()

        for query in SEARCHES[
            :QUERY_LIMIT
        ]:

            counters[
                "queries"
            ] += 1

            print()
            print(
                "=" * 80
            )

            print(
                "[BUNDLE SEARCH] "
                f"{query}"
            )

            print(
                "=" * 80
            )

            try:

                page.goto(
                    make_url(query),
                    wait_until="domcontentloaded",
                    timeout=20000,
                )

                page.wait_for_selector(
                    '[data-cy="l-card"]',
                    timeout=8000,
                )

            except PlaywrightTimeoutError:

                counters[
                    "timeouts"
                ] += 1

                print(
                    "[BUNDLE SEARCH TIMEOUT]"
                )

                continue

            except Exception as e:

                print(
                    "[BUNDLE SEARCH ERROR] "
                    f"{e}"
                )

                continue

            cards = page.locator(
                '[data-cy="l-card"]'
            )

            count = min(
                cards.count(),
                MAX_CARDS_PER_QUERY,
            )

            print(
                "Karty:",
                count
            )

            for i in range(
                count
            ):

                try:

                    card = cards.nth(i)

                    card_text = (
                        card.inner_text()
                        .strip()
                    )

                    counters[
                        "cards"
                    ] += 1

                    offer_url = (
                        get_offer_link(
                            card
                        )
                    )

                    if not offer_url:
                        continue

                    offer_id = (
                        get_offer_id(
                            offer_url
                        )
                    )

                    if not offer_id:
                        continue

                    if (
                        offer_id
                        in processed_ids
                    ):

                        counters[
                            "duplicates_run"
                        ] += 1

                        continue

                    processed_ids.add(
                        offer_id
                    )

                    lines = [
                        line.strip()
                        for line
                        in card_text.splitlines()
                        if line.strip()
                    ]

                    title = (
                        lines[0]
                        if lines
                        else ""
                    )

                    if not looks_interesting(
                        title
                    ):

                        continue

                    counters[
                        "interesting"
                    ] += 1

                    price = parse_price(
                        card_text
                    )

                    observation = (
                        observe_bundle(
                            offer_id,
                            title,
                            offer_url,
                            price,
                            query,
                        )
                    )

                    if not observation[
                        "should_queue"
                    ]:

                        continue

                    trigger = (
                        observation[
                            "trigger"
                        ]
                    )

                    if trigger == (
                        "BUNDLE_DISCOVERY"
                    ):

                        counters[
                            "new_bundle"
                        ] += 1

                    elif trigger == (
                        "BUNDLE_PRICE_DROP"
                    ):

                        counters[
                            "price_drop"
                        ] += 1

                        print(
                            "[BUNDLE PRICE DROP] "
                            f"{offer_id}: "
                            f"{observation['previous_price']} "
                            f"-> "
                            f"{price} zł"
                        )

                    if (
                        counters[
                            "queued"
                        ]
                        >= MAX_QUEUE_PER_RUN
                    ):

                        counters[
                            "queue_limit"
                        ] += 1

                        continue

                    queued = enqueue(
                        offer_id=offer_id,
                        title=title,
                        url=offer_url,
                        price=price,
                        mode="POLSKA",
                        trigger=trigger,
                    )

                    if queued:

                        counters[
                            "queued"
                        ] += 1

                        mark_bundle_queued(
                            offer_id,
                            trigger,
                        )

                        print()

                        print(
                            "[BUNDLE QUEUED]"
                        )

                        print(
                            f"ID:      {offer_id}"
                        )

                        print(
                            f"CENA:    {price} zł"
                        )

                        print(
                            f"TRIGGER: {trigger}"
                        )

                        print(
                            f"TYTUŁ:   {title}"
                        )

                        print(
                            f"URL:     {offer_url}"
                        )

                except Exception as e:

                    print(
                        "[BUNDLE CARD ERROR "
                        f"{i}] {e}"
                    )

            time.sleep(
                0.3
            )

        browser.close()

    elapsed = round(
        time.time() - start,
        2
    )

    print()
    print(
        "=" * 80
    )

    print(
        "BUNDLE FAST RADAR — KONIEC"
    )

    print(
        "=" * 80
    )

    print(
        f"Czas:              "
        f"{elapsed}s"
    )

    for key, value in (
        counters.items()
    ):

        print(
            f"{key:18}: "
            f"{value}"
        )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
