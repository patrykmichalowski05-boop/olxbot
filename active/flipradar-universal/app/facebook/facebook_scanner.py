from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from facebook.facebook_parser import parse_marketplace_card

from facebook.facebook_config import (
    SEARCHES,
    MAX_OFFERS_PER_QUERY,
    PAGE_WAIT_MS,
    SCROLL_WAIT_MS,
    SCROLLS,
)


BASE_URL = "https://www.facebook.com/marketplace/poznan/search/"


def build_url(query):
    return (
        BASE_URL
        + "?query="
        + quote_plus(query)
    )


def scan_query(page, query):

    url = build_url(query)

    print()
    print("=" * 80)
    print("FACEBOOK:", query)
    print("=" * 80)

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(
        PAGE_WAIT_MS
    )

    # Facebook doładowuje kolejne oferty przy przewijaniu.
    for _ in range(SCROLLS):
        page.mouse.wheel(
            0,
            4000
        )

        page.wait_for_timeout(
            SCROLL_WAIT_MS
        )

    links = page.locator(
        'a[href*="/marketplace/item/"]'
    )

    count = links.count()

    print(
        "LINKÓW NA STRONIE:",
        count
    )

    seen = set()
    results = []

    for i in range(count):

        if len(results) >= MAX_OFFERS_PER_QUERY:
            break

        item = links.nth(i)

        try:
            href = item.get_attribute(
                "href"
            )

            text = (
                item.inner_text(
                    timeout=2000
                )
                or ""
            ).strip()

        except Exception:
            continue

        if not href:
            continue

        # Pełny link Facebooka.
        if href.startswith("/"):
            href = (
                "https://www.facebook.com"
                + href
            )

        # Usuwamy parametry śledzące.
        href = href.split("?")[0]

        if href in seen:
            continue

        seen.add(href)

        parsed = parse_marketplace_card(text)

        if not parsed:
            continue

        results.append({
            "query": query,
            "url": href,
            "text": text,
            "price": parsed.get("price"),
            "old_price": parsed.get("old_price"),
            "title": parsed.get("title"),
            "location": parsed.get("location"),
        })

    for n, offer in enumerate(
        results,
        start=1
    ):
        print()
        print(
            f"[OFERTA {n}]"
        )

        print(
            "CENA:",
            offer.get("price")
        )

        print(
            "STARA CENA:",
            offer.get("old_price")
        )

        print(
            "TYTUŁ:",
            offer.get("title")
        )

        print(
            "LOKALIZACJA:",
            offer.get("location")
        )

        print(
            "LINK:",
            offer.get("url")
        )

    print()
    print(
        "UNIKALNYCH OFERT:",
        len(results)
    )

    return results


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        # Na razie testujemy tylko pierwsze wyszukiwanie.
        query = SEARCHES[0]

        results = scan_query(
            page,
            query
        )

        browser.close()

    print()
    print("=" * 80)
    print(
        "FACEBOOK SKAN GOTOWY | "
        f"oferty: {len(results)}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
