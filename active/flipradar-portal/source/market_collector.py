from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from urllib.parse import (
    quote,
    urljoin
)

from market_db import (
    init_market_db,
    get_offer,
    touch_offer,
    add_offer,
    stats
)

from offer_parser import extract_offer
from filters import hardware_ok

import re
import time


BASE_URL = (
    "https://www.olx.pl/elektronika/"
    "komputery/komputery-stacjonarne/"
)


SEARCHES = [
    "komputer gamingowy",
    "komputer RTX",
    "komputer Ryzen",

    "RTX 2060",
    "RTX 2060 Super",
    "RTX 2070",
    "RTX 2070 Super",
    "RTX 2080",
    "RTX 2080 Ti",

    "RTX 3050",
    "RTX 3060",
    "RTX 3060 Ti",
    "RTX 3070",
    "RTX 3070 Ti",
    "RTX 3080",
    "RTX 3080 Ti",

    "RTX 4060",
    "RTX 4060 Ti",
    "RTX 4070",
    "RTX 4070 Super",
    "RTX 4080",

    "RTX 5060",
    "RTX 5060 Ti",
    "RTX 5070",

    "RX 6600",
    "RX 6600 XT",
    "RX 6650 XT",
    "RX 6700 XT",
    "RX 6750 XT",

    "RX 7600",
    "RX 7700 XT",
    "RX 7800 XT",

    "Ryzen 5 3600",
    "Ryzen 5 5500",
    "Ryzen 5 5600",
    "Ryzen 7 5700",
    "Ryzen 7 5800",

    "i5 9400F",
    "i5 10400F",
    "i5 11400F",
    "i5 12400F",
    "i5 13400F",
    "i5 14400F",
]


MAX_DETAILS_PER_QUERY = 10
MAX_DETAILS_TOTAL = 140


def make_url(query):

    return (
        BASE_URL
        + "?q="
        + quote(query)
        + "&search%5Border%5D=created_at:desc"
    )


def clean_url(url):
    return url.split("?")[0]


def get_offer_id(url):
    """
    Prawdziwe ID OLX:

    ...-CID99-ID1cy7iC.html

    CID99 NIE jest ID ogłoszenia.
    """

    match = re.search(
        r"-CID\d+-(ID[a-zA-Z0-9]+)\.html",
        url,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    matches = re.findall(
        r"ID[a-zA-Z0-9]+",
        url,
        re.IGNORECASE
    )

    matches = [
        value
        for value in matches
        if value.upper() != "ID99"
    ]

    if matches:
        return matches[-1]

    return None


def get_offer_link(card):

    links = card.locator(
        'a[href*="/d/oferta/"]'
    )

    if links.count() == 0:
        return None

    for i in range(
        links.count()
    ):

        href = (
            links.nth(i)
            .get_attribute("href")
        )

        if (
            href
            and "/d/oferta/" in href
            and "ID" in href
        ):

            return clean_url(
                urljoin(
                    "https://www.olx.pl",
                    href
                )
            )

    return None


def parse_card_price(text):

    match = re.search(
        r"(\d[\d\s]*(?:[,.]\d{2})?)\s*zł",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = (
        match.group(1)
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return int(float(value))
    except:
        return None


def card_has_shipping(text):

    text = text.lower()

    keywords = [
        "pakietem ochronnym",
        "pakiet ochronny",
        "przesyłka olx",
        "przesylka olx",
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


def looks_like_full_pc(
    title,
    cpu,
    gpu,
    ram,
    price
):

    if not title:
        return False

    title_l = (
        title.lower()
    )

    bad_phrases = [
        "sama karta",
        "karta graficzna",
        "sprzedam procesor",
        "sam procesor",
        "płyta główna",
        "plyta glowna",
        "sama obudowa",
        "sam zasilacz",
    ]

    if any(
        phrase in title_l
        for phrase in bad_phrases
    ):
        return False

    if not cpu:
        return False

    if not gpu:
        return False

    if ram is None:
        return False

    if ram < 16:
        return False

    if price is None:
        return False

    # Baza rynku:
    # ekstremalne okazje poniżej 700 zł
    # zostawiamy radarowi flipów.
    if price < 700:
        return False

    if price > 15000:
        return False

    return True


def main():

    init_market_db()

    processed_ids = set()

    counters = {
        "cards": 0,
        "duplicates": 0,
        "no_shipping_card": 0,
        "details_opened": 0,
        "details_failed": 0,
        "hardware_rejected": 0,
        "shipping_rejected": 0,
        "pc_rejected": 0,
        "saved": 0,
        "timeouts": 0,
    }

    with sync_playwright() as p:

        browser = (
            p.chromium.launch(
                headless=True
            )
        )

        context = (
            browser.new_context(
                viewport={
                    "width": 1400,
                    "height": 900
                },
                locale="pl-PL"
            )
        )

        search_page = (
            context.new_page()
        )

        detail_page = (
            context.new_page()
        )

        total_details = 0

        for query in SEARCHES:

            if (
                total_details
                >= MAX_DETAILS_TOTAL
            ):

                print()
                print(
                    "[LIMIT] "
                    "Osiągnięto globalny limit."
                )

                break

            print()
            print("=" * 75)
            print(
                f"[MARKET] {query}"
            )

            try:

                search_page.goto(
                    make_url(query),
                    wait_until="domcontentloaded",
                    timeout=20000
                )

                search_page.wait_for_selector(
                    '[data-cy="l-card"]',
                    timeout=8000
                )

            except PlaywrightTimeoutError:

                print(
                    f"[TIMEOUT] "
                    f"{query} — pomijam"
                )

                counters[
                    "timeouts"
                ] += 1

                time.sleep(2)
                continue

            except Exception as e:

                print(
                    f"[ERROR SEARCH] "
                    f"{query}: {e}"
                )

                time.sleep(2)
                continue

            cards = search_page.locator(
                '[data-cy="l-card"]'
            )

            count = cards.count()

            print(
                f"Wyników: {count}"
            )

            details_this_query = 0

            for i in range(count):

                if (
                    details_this_query
                    >= MAX_DETAILS_PER_QUERY
                ):
                    break

                if (
                    total_details
                    >= MAX_DETAILS_TOTAL
                ):
                    break

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

                    # =================================
                    # DUPLIKAT W TYM SAMYM PRZEBIEGU
                    # =================================

                    if (
                        offer_id
                        in processed_ids
                    ):

                        counters[
                            "duplicates"
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

                    card_title = (
                        lines[0]
                        if lines
                        else ""
                    )

                    card_price = (
                        parse_card_price(
                            card_text
                        )
                    )

                    # =================================
                    # JUŻ W MARKET.DB
                    # =================================

                    old = get_offer(
                        offer_id
                    )

                    if old:

                        touch_offer(
                            offer_id,
                            card_title,
                            card_price,
                            offer_url,
                            query
                        )

                        continue

                    # =================================
                    # FILTR SHIPPING JUŻ NA KARCIE
                    # =================================

                    if not card_has_shipping(
                        card_text
                    ):

                        counters[
                            "no_shipping_card"
                        ] += 1

                        continue

                    # =================================
                    # OTWIERAMY SZCZEGÓŁY
                    # =================================

                    details_this_query += 1
                    total_details += 1

                    counters[
                        "details_opened"
                    ] += 1

                    print()
                    print(
                        f"[OTWIERAM "
                        f"{total_details}] "
                        f"{offer_id}"
                    )

                    print(
                        offer_url
                    )

                    try:

                        details = (
                            extract_offer(
                                detail_page,
                                offer_url
                            )
                        )

                    except PlaywrightTimeoutError:

                        print(
                            "[TIMEOUT OFERTA]"
                        )

                        counters[
                            "timeouts"
                        ] += 1

                        continue

                    except Exception as e:

                        print(
                            f"[ERROR OFERTA] "
                            f"{e}"
                        )

                        counters[
                            "details_failed"
                        ] += 1

                        continue

                    if not details:

                        counters[
                            "details_failed"
                        ] += 1

                        continue

                    # Cena z listingu OLX
                    if (
                        card_price
                        is not None
                    ):

                        details[
                            "price"
                        ] = card_price

                    if not details.get(
                        "title"
                    ):

                        details[
                            "title"
                        ] = card_title

                    # =================================
                    # CPU / RAM
                    # =================================

                    ok, reasons = (
                        hardware_ok(
                            details
                        )
                    )

                    if not ok:

                        counters[
                            "hardware_rejected"
                        ] += 1

                        print(
                            "[ODRZUT HARDWARE] "
                            f"{details.get('cpu')} | "
                            f"{details.get('ram')}"
                        )

                        continue

                    # =================================
                    # SHIPPING — DRUGA WERYFIKACJA
                    # =================================

                    if not details.get(
                        "shipping"
                    ):

                        counters[
                            "shipping_rejected"
                        ] += 1

                        print(
                            "[ODRZUT SHIPPING]"
                        )

                        continue

                    # =================================
                    # CZY TO PEŁNY PC
                    # =================================

                    if not looks_like_full_pc(
                        title=details.get(
                            "title"
                        ),
                        cpu=details.get(
                            "cpu"
                        ),
                        gpu=details.get(
                            "gpu"
                        ),
                        ram=details.get(
                            "ram"
                        ),
                        price=details.get(
                            "price"
                        )
                    ):

                        counters[
                            "pc_rejected"
                        ] += 1

                        print(
                            "[ODRZUT PC] "
                            f"{details.get('cpu')} | "
                            f"{details.get('gpu')} | "
                            f"{details.get('ram')} | "
                            f"{details.get('price')}"
                        )

                        continue

                    # =================================
                    # MARKET.DB
                    # =================================

                    add_offer(
                        offer_id=offer_id,

                        title=details.get(
                            "title"
                        ),

                        url=offer_url,

                        price=details.get(
                            "price"
                        ),

                        cpu=details.get(
                            "cpu"
                        ),

                        gpu=details.get(
                            "gpu"
                        ),

                        ram=details.get(
                            "ram"
                        ),

                        disks=details.get(
                            "disks"
                        ),

                        shipping=True,

                        source_query=query
                    )

                    counters[
                        "saved"
                    ] += 1

                    print(
                        "[DODANO] "
                        f"{details.get('cpu')} | "
                        f"{details.get('gpu')} | "
                        f"{details.get('ram')} GB | "
                        f"{details.get('price')} zł"
                    )

                except Exception as e:

                    print(
                        f"[ERROR KARTA "
                        f"{i}] {e}"
                    )

            time.sleep(1)

        browser.close()

    print()
    print("=" * 75)
    print(
        "MARKET COLLECTOR — KONIEC"
    )
    print("=" * 75)

    for key, value in (
        counters.items()
    ):

        print(
            f"{key:22} : "
            f"{value}"
        )

    print()

    print(
        "MARKET.DB:",
        stats()
    )

    print("=" * 75)


if __name__ == "__main__":
    main()
