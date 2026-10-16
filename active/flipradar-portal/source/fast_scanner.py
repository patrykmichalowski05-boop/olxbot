from playwright.sync_api import (
    sync_playwright
)

from urllib.parse import urljoin

import re
import time


from fast_db import (
    init_db,
    count_offers,
    observe_offer,
    enqueue,
    queue_stats,
)

from browser_utils import (
    block_heavy_resources
)

from candidate_prefilter import (
    prefilter_candidate,
)


# ============================================================
# CONFIG
# ============================================================

LOCAL_URL = (
    "https://www.olx.pl/elektronika/komputery/"
    "komputery-stacjonarne/kornik/"
    "?search%5Bdist%5D=30"
    "&search%5Border%5D=created_at:desc"
)

POLSKA_URL = (
    "https://www.olx.pl/elektronika/komputery/"
    "komputery-stacjonarne/"
    "?search%5Border%5D=created_at:desc"
)


MAX_CARDS = 60


# ============================================================
# URL
# ============================================================

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
            and
            "/d/oferta/" in href
            and
            "ID" in href
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

        return int(
            float(value)
        )

    except Exception:

        return None


# ============================================================
# FEED
# ============================================================

def scan_feed(
    page,
    mode,
    url,
    bootstrap,
):

    print()

    print(
        "=" * 75
    )

    print(
        f"FAST RADAR: {mode}"
    )

    print(
        "=" * 75
    )

    counters = {
        "cards": 0,
        "new": 0,
        "drops": 0,
        "queued": 0,
    }

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=20000,
        )

        page.wait_for_selector(
            '[data-cy="l-card"]',
            timeout=8000,
        )

    except Exception as e:

        print(
            "[FAST FEED ERROR]",
            e
        )

        return counters

    cards = page.locator(
        '[data-cy="l-card"]'
    )

    count = min(
        cards.count(),
        MAX_CARDS,
    )

    print(
        "Karty:",
        count
    )

    processed = set()

    for i in range(count):

        try:

            card = cards.nth(i)

            text = (
                card.inner_text()
                .strip()
            )

            url = get_offer_link(
                card
            )

            if not url:
                continue

            offer_id = get_offer_id(
                url
            )

            if not offer_id:
                continue

            if offer_id in processed:
                continue

            processed.add(
                offer_id
            )

            counters[
                "cards"
            ] += 1

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            title = (
                lines[0]
                if lines
                else "Brak tytułu"
            )

            price = parse_price(
                text
            )

            prefilter = prefilter_candidate(
                title=title,
                price=price,
                trigger="NEW",
            )

            if prefilter.get("skip"):

                print(
                    "[FAST PREFILTER] "
                    f"{offer_id} | "
                    f"{prefilter.get('reason')} | "
                    f"{price} zł | "
                    f"{title}"
                )

                # Nadal zapamiętujemy ofertę,
                # żeby nie wypisywać jej jako NEW
                # podczas każdego kolejnego skanu.

                observe_offer(
                    offer_id,
                    title,
                    price,
                    url,
                )

                continue

            result = observe_offer(
                offer_id,
                title,
                price,
                url,
            )

            # ================================================
            # NOWA
            # ================================================

            if result["new"]:

                counters[
                    "new"
                ] += 1

                print(
                    "[FAST NEW] "
                    f"{offer_id} | "
                    f"{price} zł | "
                    f"{title}"
                )

                # Pierwsze uruchomienie tylko
                # buduje bazę startową.
                if not bootstrap:

                    queued = enqueue(
                        offer_id,
                        title,
                        url,
                        price,
                        mode,
                        "NEW",
                    )

                    if queued:

                        counters[
                            "queued"
                        ] += 1

            # ================================================
            # PRICE DROP
            # ================================================

            elif result[
                "price_drop"
            ]:

                counters[
                    "drops"
                ] += 1

                print(
                    "[FAST PRICE DROP] "
                    f"{offer_id}: "
                    f"{result['previous_price']} "
                    f"-> "
                    f"{result['current_price']} zł"
                )

                queued = enqueue(
                    offer_id,
                    title,
                    url,
                    price,
                    mode,
                    "PRICE_DROP",
                )

                if queued:

                    counters[
                        "queued"
                    ] += 1

        except Exception as e:

            print(
                f"[FAST CARD ERROR {i}] "
                f"{e}"
            )

    return counters


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()

    # Jeśli FAST DB jest pusta,
    # pierwszy przebieg jest bootstrapem.
    #
    # Nie chcemy po uruchomieniu wrzucić
    # 100 starych ofert do kolejki.

    bootstrap = (
        count_offers() == 0
    )

    if bootstrap:

        print()
        print(
            "FAST RADAR — BOOTSTRAP"
        )

        print(
            "Pierwszy przebieg tylko "
            "buduje bazę ofert."
        )

    start = time.time()

    totals = {
        "cards": 0,
        "new": 0,
        "drops": 0,
        "queued": 0,
    }

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

        local = scan_feed(
            page,
            "LOCAL",
            LOCAL_URL,
            bootstrap,
        )

        national = scan_feed(
            page,
            "POLSKA",
            POLSKA_URL,
            bootstrap,
        )

        browser.close()

    for result in [
        local,
        national,
    ]:

        for key in totals:

            totals[key] += (
                result[key]
            )

    elapsed = round(
        time.time() - start,
        2
    )

    print()
    print(
        "=" * 75
    )

    print(
        "FAST RADAR GOTOWY"
    )

    print(
        f"Czas:        {elapsed}s"
    )

    print(
        f"Karty:       {totals['cards']}"
    )

    print(
        f"Nowe:        {totals['new']}"
    )

    print(
        f"Price drop:  {totals['drops']}"
    )

    print(
        f"Do kolejki:  {totals['queued']}"
    )

    print(
        "Queue:",
        queue_stats()
    )

    print(
        "=" * 75
    )


if __name__ == "__main__":

    main()
