import os
import re
import time

from urllib.parse import (
    quote,
    urljoin,
)

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ============================================================
# MARKET DB
# ============================================================

from market_db import (
    init_market_db,
    get_offer,
    add_offer,
    touch_offer,
    stats,
)


# ============================================================
# OFFER PARSER
# ============================================================

from offer_parser import (
    extract_offer,
)

from market_reference_quality import (
    is_placeholder_title,
    select_market_card_title,
    reject_reason,
)


# ============================================================
# SPEC RECOVERY
# ============================================================

from spec_recovery import (
    missing_specs,
    recover_missing_specs,
)


# ============================================================
# BROWSER
# ============================================================

from browser_utils import (
    block_heavy_resources,
)


# ============================================================
# BUNDLE DETECTOR
# ============================================================

from bundle_detector import (
    analyze_bundle,
)


# ============================================================
# CONFIG
# ============================================================

BASE_URL = (
    "https://www.olx.pl/elektronika/"
    "komputery/komputery-stacjonarne/"
)


SEARCHES = [
    # --------------------------------------------------------
    # OGÓLNE
    # --------------------------------------------------------

    "komputer gamingowy",
    "komputer RTX",
    "komputer Ryzen",

    # --------------------------------------------------------
    # NVIDIA RTX 20
    # --------------------------------------------------------

    "RTX 2060",
    "RTX 2060 Super",
    "RTX 2070",
    "RTX 2070 Super",
    "RTX 2080",
    "RTX 2080 Ti",

    # --------------------------------------------------------
    # NVIDIA RTX 30
    # --------------------------------------------------------

    "RTX 3050",
    "RTX 3060",
    "RTX 3060 Ti",
    "RTX 3070",
    "RTX 3070 Ti",
    "RTX 3080",
    "RTX 3080 Ti",
    "RTX 3090",

    # --------------------------------------------------------
    # NVIDIA RTX 40
    # --------------------------------------------------------

    "RTX 4060",
    "RTX 4060 Ti",
    "RTX 4070",
    "RTX 4070 Super",
    "RTX 4070 Ti",
    "RTX 4070 Ti Super",
    "RTX 4080",
    "RTX 4080 Super",

    # --------------------------------------------------------
    # NVIDIA RTX 50
    # --------------------------------------------------------

    "RTX 5060",
    "RTX 5060 Ti",
    "RTX 5070",

    # --------------------------------------------------------
    # AMD
    # --------------------------------------------------------

    "RX 6600",
    "RX 6600 XT",
    "RX 6650 XT",
    "RX 6700 XT",
    "RX 6750 XT",
    "RX 6800",
    "RX 6800 XT",

    "RX 7600",
    "RX 7600 XT",
    "RX 7700 XT",
    "RX 7800 XT",

    # --------------------------------------------------------
    # AMD CPU
    # --------------------------------------------------------

    "Ryzen 5 3600",
    "Ryzen 5 5500",
    "Ryzen 5 5600",
    "Ryzen 5 5600X",
    "Ryzen 7 5700X",
    "Ryzen 7 5800X",

    # --------------------------------------------------------
    # INTEL CPU
    # --------------------------------------------------------

    "i5 9400F",
    "i5 10400F",
    "i5 11400F",
    "i5 12400F",
    "i5 13400F",
    "i5 14400F",
]


# ============================================================
# LIMITS
# ============================================================

QUERY_LIMIT = int(
    os.getenv(
        "MARKET_QUERY_LIMIT",
        str(len(SEARCHES)),
    )
)


MAX_DETAILS_TOTAL = int(
    os.getenv(
        "MARKET_MAX_DETAILS",
        "140",
    )
)


MAX_DETAILS_PER_QUERY = int(
    os.getenv(
        "MARKET_MAX_DETAILS_PER_QUERY",
        "10",
    )
)


MAX_AI_RECOVERY = int(
    os.getenv(
        "MARKET_AI_LIMIT",
        "20",
    )
)


# ============================================================
# URL
# ============================================================

def make_url(
    query,
):

    return (
        BASE_URL
        + "?q="
        + quote(query)
        + "&search%5Border%5D="
        + "created_at:desc"
    )


def clean_url(
    url,
):

    if not url:
        return None

    return url.split("?")[0]


# ============================================================
# OFFER ID
# ============================================================

def get_offer_id(
    url,
):

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


# ============================================================
# OFFER LINK
# ============================================================

def get_offer_link(
    card,
):

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
# CARD PRICE
# ============================================================

def parse_card_price(
    text,
):

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
# SHIPPING CARD
# ============================================================

def card_has_shipping(
    text,
):

    text = str(
        text or ""
    ).lower()

    phrases = [
        "pakietem ochronnym",
        "pakiet ochronny",
        "przesyłka olx",
        "przesylka olx",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


# ============================================================
# FULL PC FILTER
# ============================================================

def looks_like_full_pc(
    details,
):

    title = str(
        details.get(
            "title",
            "",
        )
    ).lower()

    bad_phrases = [
        "sama karta",
        "karta graficzna",
        "sprzedam kartę",
        "sprzedam karte",

        "sam procesor",
        "sprzedam procesor",

        "płyta główna",
        "plyta glowna",

        "sama obudowa",
        "obudowa komputerowa",

        "sam zasilacz",

        "zestaw części",
        "zestaw czesci",
    ]

    if any(
        phrase in title
        for phrase in bad_phrases
    ):

        return False

    cpu = details.get(
        "cpu"
    )

    gpu = details.get(
        "gpu"
    )

    ram = details.get(
        "ram"
    )

    price = details.get(
        "price"
    )

    if not cpu:
        return False

    if not gpu:
        return False

    try:

        ram = int(
            ram
        )

    except Exception:

        return False

    if ram < 16:
        return False

    try:

        price = int(
            price
        )

    except Exception:

        return False

    if price < 700:
        return False

    if price > 15000:
        return False

    return True


# ============================================================
# AI SPEC RECOVERY
# ============================================================

def recover_specs(
    details,
    counters,
):

    from copy import deepcopy
    original_details = deepcopy(details)

    missing = missing_specs(
        details
    )

    if not missing:

        return details

    if (
        counters[
            "ai_recovery"
        ]
        >= MAX_AI_RECOVERY
    ):

        counters[
            "ai_limit_skipped"
        ] += 1

        return details

    print(
        "[SPEC AI] "
        + ", ".join(
            missing
        )
    )

    counters[
        "ai_recovery"
    ] += 1

    try:

        result = recover_missing_specs(
            details
        )

    except Exception as e:

        counters[
            "ai_failed"
        ] += 1

        print(
            "[SPEC AI ERROR] "
            f"{e}"
        )

        return details

    if not result.get(
        "ok"
    ):

        counters[
            "ai_failed"
        ] += 1

        print(
            "[SPEC AI ERROR] "
            + result.get(
                "reason",
                "unknown",
            )
        )

        return details

    recovered = (
        result.get(
            "details"
        )
        or details
    )

    for item in (
        result.get(
            "filled"
        )
        or []
    ):

        print(
            "[SPEC AI OK] "
            f"{item.get('field')}="
            f"{item.get('value')}"
        )

    # AI moze tylko uzupelniac brakujace wartosci.
    # Nigdy nie podmienia juz rozpoznanych danych.
    safe_details = deepcopy(original_details)

    if isinstance(recovered, dict):
        for key, value in recovered.items():
            if key in ("title", "price", "url", "shipping"):
                continue

            current = safe_details.get(key)

            if current is None or current == "" or current == []:
                if value is not None and value != "" and value != []:
                    safe_details[key] = value

    return safe_details


# ============================================================
# MAIN
# ============================================================

def main():

    init_market_db()

    counters = {

        # feed
        "cards":
            0,

        "duplicates_run":
            0,

        # known
        "known_unchanged":
            0,

        "known_price_changed":
            0,

        # feed filters
        "no_shipping_card":
            0,

        # details
        "details_opened":
            0,

        "details_failed":
            0,

        # AI
        "ai_recovery":
            0,

        "ai_failed":
            0,

        "ai_limit_skipped":
            0,

        # rejects
        "shipping_rejected":
            0,

        "pc_rejected":
            0,

        "bundle_rejected":
            0,

        # save
        "saved_new":
            0,

        "saved_updated":
            0,

        # browser
        "timeouts":
            0,
    }

    processed_ids = set()

    # ========================================================
    # PLAYWRIGHT
    # ========================================================

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

        search_page = (
            context.new_page()
        )

        detail_page = (
            context.new_page()
        )

        total_details = 0

        queries = SEARCHES[
            :QUERY_LIMIT
        ]

        # ====================================================
        # SEARCH LOOP
        # ====================================================

        for query_number, query in enumerate(
            queries,
            start=1,
        ):

            # ------------------------------------------------
            # GLOBAL LIMIT
            # ------------------------------------------------

            if (
                total_details
                >= MAX_DETAILS_TOTAL
            ):

                print()

                print(
                    "[GLOBAL LIMIT]"
                )

                break

            print()

            print(
                "=" * 80
            )

            print(
                f"[MARKET "
                f"{query_number}/"
                f"{len(queries)}] "
                f"{query}"
            )

            print(
                "=" * 80
            )

            # ------------------------------------------------
            # OPEN SEARCH
            # ------------------------------------------------

            try:

                search_page.goto(
                    make_url(
                        query
                    ),

                    wait_until=
                        "domcontentloaded",

                    timeout=20000,
                )

                search_page.wait_for_selector(
                    '[data-cy="l-card"]',
                    timeout=8000,
                )

            except PlaywrightTimeoutError:

                counters[
                    "timeouts"
                ] += 1

                print(
                    "[SEARCH TIMEOUT]"
                )

                continue

            except Exception as e:

                print(
                    "[SEARCH ERROR] "
                    f"{e}"
                )

                continue

            # ------------------------------------------------
            # CARDS
            # ------------------------------------------------

            cards = (
                search_page.locator(
                    '[data-cy="l-card"]'
                )
            )

            count = cards.count()

            print(
                f"Wyników: {count}"
            )

            details_this_query = 0

            # =================================================
            # CARD LOOP
            # =================================================

            for i in range(
                count
            ):

                if (
                    details_this_query
                    >=
                    MAX_DETAILS_PER_QUERY
                ):

                    break

                if (
                    total_details
                    >=
                    MAX_DETAILS_TOTAL
                ):

                    break

                try:

                    card = (
                        cards.nth(i)
                    )

                    card_text = (
                        card.inner_text()
                        .strip()
                    )

                    counters[
                        "cards"
                    ] += 1

                    # ----------------------------------------
                    # URL
                    # ----------------------------------------

                    offer_url = (
                        get_offer_link(
                            card
                        )
                    )

                    if not offer_url:

                        continue

                    # ----------------------------------------
                    # ID
                    # ----------------------------------------

                    offer_id = (
                        get_offer_id(
                            offer_url
                        )
                    )

                    if not offer_id:

                        continue

                    # ----------------------------------------
                    # DEDUPE RUN
                    # ----------------------------------------

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

                    # ----------------------------------------
                    # TITLE
                    # ----------------------------------------

                    lines = [
                        line.strip()
                        for line
                        in card_text.splitlines()
                        if line.strip()
                    ]

                    card_title = select_market_card_title(
                        card_text
                    )

                    # ----------------------------------------
                    # PRICE
                    # ----------------------------------------

                    card_price = (
                        parse_card_price(
                            card_text
                        )
                    )

                    # ----------------------------------------
                    # EXISTING MARKET OFFER
                    # ----------------------------------------

                    old = get_offer(
                        offer_id
                    )

                    if old:

                        old_price = (
                            old["price"]
                        )

                        price_changed = (
                            card_price
                            is not None
                            and
                            old_price
                            is not None
                            and
                            card_price
                            != old_price
                        )

                        missing_old_specs = (
                            not old["cpu"]
                            or
                            not old["gpu"]
                            or
                            not old["ram"]
                        )

                        # ------------------------------------
                        # KNOWN + UNCHANGED
                        # ------------------------------------

                        if (
                            not price_changed
                            and
                            not missing_old_specs
                            and
                            reject_reason(old) not in (
                                "GPU_MISMATCH",
                                "RAM_MISMATCH",
                                "GENERIC_TITLE",
                            )
                        ):

                            touch_offer(
                                offer_id=
                                    offer_id,

                                title=old["title"],

                                price=
                                    card_price,

                                url=
                                    offer_url,

                                source_query=
                                    query,
                            )

                            counters[
                                "known_unchanged"
                            ] += 1

                            continue

                        # ------------------------------------
                        # PRICE CHANGE
                        # ------------------------------------

                        if price_changed:

                            counters[
                                "known_price_changed"
                            ] += 1

                            print()

                            print(
                                "[PRICE CHANGE] "
                                f"{offer_id}: "
                                f"{old_price} "
                                f"-> "
                                f"{card_price}"
                            )

                    # ----------------------------------------
                    # SHIPPING CARD FILTER
                    # ----------------------------------------

                    if not card_has_shipping(
                        card_text
                    ):

                        counters[
                            "no_shipping_card"
                        ] += 1

                        continue

                    # ----------------------------------------
                    # DETAIL LIMIT
                    # ----------------------------------------

                    details_this_query += 1

                    total_details += 1

                    counters[
                        "details_opened"
                    ] += 1

                    print()

                    print(
                        f"[OPEN "
                        f"{total_details}] "
                        f"{offer_id}"
                    )

                    print(
                        card_title
                    )

                    print(
                        f"{card_price} zł"
                    )

                    # ----------------------------------------
                    # OPEN FULL OFFER
                    # ----------------------------------------

                    try:

                        details = (
                            extract_offer(
                                detail_page,
                                offer_url,
                            )
                        )

                    except PlaywrightTimeoutError:

                        counters[
                            "timeouts"
                        ] += 1

                        print(
                            "[DETAIL TIMEOUT]"
                        )

                        continue

                    except Exception as e:

                        counters[
                            "details_failed"
                        ] += 1

                        print(
                            "[DETAIL ERROR] "
                            f"{e}"
                        )

                        continue

                    if not details:

                        counters[
                            "details_failed"
                        ] += 1

                        continue

                    # ----------------------------------------
                    # CARD PRICE MA PIERWSZEŃSTWO
                    # ----------------------------------------

                    if (
                        card_price
                        is not None
                    ):

                        details[
                            "price"
                        ] = card_price

                    if is_placeholder_title(
                        details.get("title")
                    ):
                        details["title"] = card_title

                    # ----------------------------------------
                    # AI SPEC RECOVERY
                    # ----------------------------------------

                    details = recover_specs(
                        details,
                        counters,
                    )

                    # ========================================
                    # BUNDLE PROTECTION
                    # ========================================

                    bundle = analyze_bundle(
                        details
                    )

                    if bundle.get(
                        "strong_bundle"
                    ):

                        counters[
                            "bundle_rejected"
                        ] += 1

                        print(
                            "[REJECT MARKET BUNDLE]"
                        )

                        print(
                            "Score: "
                            f"{bundle.get('score')}"
                        )

                        print(
                            "Confidence: "
                            f"{bundle.get('confidence')}"
                        )

                        print(
                            "Extras: "
                            f"{bundle.get('accessory_quick_value')} zł"
                        )

                        for item in (
                            bundle.get(
                                "items"
                            )
                            or []
                        ):

                            print(
                                "  + "
                                f"{item.get('label')} "
                                f"~"
                                f"{item.get('quick_value')} zł"
                            )

                        # WAŻNE:
                        #
                        # setup nie trafia do market.db,
                        # bo jego cena zawiera np.
                        # monitor / kierownicę / HOTAS.
                        #
                        # Takie rekordy zawyżałyby ceny
                        # zwykłych PC.

                        continue

                    # ----------------------------------------
                    # SHIPPING DETAIL
                    # ----------------------------------------

                    if not details.get(
                        "shipping"
                    ):

                        counters[
                            "shipping_rejected"
                        ] += 1

                        print(
                            "[REJECT SHIPPING]"
                        )

                        continue

                    # ----------------------------------------
                    # FULL PC
                    # ----------------------------------------

                    if not looks_like_full_pc(
                        details
                    ):

                        counters[
                            "pc_rejected"
                        ] += 1

                        print(
                            "[REJECT PC] "
                            f"CPU="
                            f"{details.get('cpu')} | "
                            f"GPU="
                            f"{details.get('gpu')} | "
                            f"RAM="
                            f"{details.get('ram')} | "
                            f"CENA="
                            f"{details.get('price')}"
                        )

                        continue

                    # ========================================
                    # SAVE MARKET
                    # ========================================

                    market_problem = reject_reason(
                        details
                    )

                    if market_problem:
                        print(
                            "[REJECT MARKET QUALITY] "
                            + market_problem
                        )
                        continue

                    existed_before = (
                        old is not None
                    )

                    result = add_offer(
                        offer_id=
                            offer_id,

                        title=
                            details.get(
                                "title"
                            ),

                        url=
                            offer_url,

                        price=
                            details.get(
                                "price"
                            ),

                        cpu=
                            details.get(
                                "cpu"
                            ),

                        gpu=
                            details.get(
                                "gpu"
                            ),

                        ram=
                            details.get(
                                "ram"
                            ),

                        disks=
                            details.get(
                                "disks"
                            ),

                        shipping=True,

                        source_query=
                            query,
                    )

                    if existed_before:

                        counters[
                            "saved_updated"
                        ] += 1

                    else:

                        counters[
                            "saved_new"
                        ] += 1

                    print(
                        "[MARKET SAVED] "
                        f"{details.get('cpu')} | "
                        f"{details.get('gpu')} | "
                        f"{details.get('ram')} GB | "
                        f"{details.get('price')} zł | "
                        f"{result}"
                    )

                except Exception as e:

                    print(
                        f"[CARD ERROR {i}] "
                        f"{e}"
                    )

            # Krótka przerwa między query.

            time.sleep(
                0.5
            )

        # ====================================================
        # CLOSE
        # ====================================================

        browser.close()

    # ========================================================
    # SUMMARY
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "MARKET COLLECTOR V2 — KONIEC"
    )

    print(
        "=" * 80
    )

    for key, value in (
        counters.items()
    ):

        print(
            f"{key:25}: "
            f"{value}"
        )

    print()

    print(
        "MARKET.DB:",
        stats()
    )

    print(
        "=" * 80
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
