from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from datetime import (
    datetime,
    timedelta
)

from market_db import (
    init_market_db,
    get_stale_active_offers,
    mark_verified_active,
    mark_verified_inactive,
    mark_verification_failure,
    stats
)

from browser_utils import (
    block_heavy_resources
)


# Oferta musi być niewidziana minimum tyle,
# zanim zaczniemy ją weryfikować.
STALE_HOURS = 24

# Nie otwieramy setek URL naraz.
MAX_VERIFY = 30


REMOVED_PHRASES = [
    "ogłoszenie nie jest już dostępne",
    "ogloszenie nie jest juz dostepne",

    "to ogłoszenie nie jest już dostępne",
    "to ogloszenie nie jest juz dostepne",

    "oferta jest nieaktualna",

    "strona nie istnieje",

    "nie znaleźliśmy tego ogłoszenia",
    "nie znalezlismy tego ogloszenia",
]


def page_is_removed(
    page,
    response
):

    # ==========================================
    # HTTP
    # ==========================================

    if response:

        status = response.status

        if status in {
            404,
            410
        }:

            return (
                True,
                f"HTTP_{status}"
            )

    # ==========================================
    # TREŚĆ STRONY
    # ==========================================

    try:

        text = (
            page.locator("body")
            .inner_text(
                timeout=5000
            )
            .lower()
        )

    except:

        text = ""

    for phrase in REMOVED_PHRASES:

        if phrase in text:

            return (
                True,
                f"TEXT:{phrase}"
            )

    return (
        False,
        None
    )


def main():

    init_market_db()

    cutoff = (
        datetime.now()
        - timedelta(
            hours=STALE_HOURS
        )
    ).isoformat(
        timespec="seconds"
    )

    offers = (
        get_stale_active_offers(
            stale_before=cutoff,
            limit=MAX_VERIFY
        )
    )

    print(
        f"Do weryfikacji: "
        f"{len(offers)}"
    )

    counters = {
        "active": 0,
        "inactive": 0,
        "errors": 0
    }

    if not offers:

        print(
            "Brak starych ofert "
            "do sprawdzenia."
        )

        print(
            stats()
        )

        return

    with sync_playwright() as p:

        browser = (
            p.chromium.launch(
                headless=True
            )
        )

        context = (
            browser.new_context(
                viewport={
                    "width": 1100,
                    "height": 700
                },
                locale="pl-PL",
                service_workers="block"
            )
        )

        block_heavy_resources(
            context
        )

        page = (
            context.new_page()
        )

        for offer in offers:

            offer_id = (
                offer["offer_id"]
            )

            url = (
                offer["url"]
            )

            print()
            print(
                f"[VERIFY] "
                f"{offer_id}"
            )

            print(
                url
            )

            try:

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=20000
                )

                removed, reason = (
                    page_is_removed(
                        page,
                        response
                    )
                )

                if removed:

                    print(
                        "[INACTIVE] "
                        + str(reason)
                    )

                    mark_verified_inactive(
                        offer_id,
                        reason
                    )

                    counters[
                        "inactive"
                    ] += 1

                else:

                    print(
                        "[ACTIVE]"
                    )

                    mark_verified_active(
                        offer_id
                    )

                    counters[
                        "active"
                    ] += 1

            except PlaywrightTimeoutError:

                print(
                    "[VERIFY TIMEOUT]"
                )

                mark_verification_failure(
                    offer_id,
                    "TIMEOUT"
                )

                counters[
                    "errors"
                ] += 1

            except Exception as e:

                print(
                    f"[VERIFY ERROR] {e}"
                )

                mark_verification_failure(
                    offer_id,
                    e
                )

                counters[
                    "errors"
                ] += 1

        browser.close()

    print()
    print("=" * 70)

    print(
        "LIFECYCLE GOTOWY"
    )

    print(
        counters
    )

    print(
        "MARKET:",
        stats()
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
