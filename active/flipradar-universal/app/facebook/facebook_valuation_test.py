from playwright.sync_api import sync_playwright

from facebook.facebook_config import SEARCHES
from facebook.facebook_scanner import scan_query
from facebook.facebook_detail_parser import extract_detail_metadata
from facebook.facebook_specs_parser import parse_pc_specs

from filters import hardware_ok
from valuation_v3 import estimate_flip_v3


MAX_TEST_OFFERS = 10


def main():

    print("=" * 80)
    print("FACEBOOK VALUATION TEST")
    print("=" * 80)

    query = SEARCHES[0]

    print()
    print("SZUKAM:")
    print(query)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        search_page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        detail_page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        # ====================================================
        # 1. POBIERAMY LISTĘ MARKETPLACE
        # ====================================================

        offers = scan_query(
            search_page,
            query
        )

        print()
        print(
            "ŁĄCZNIE ZNALEZIONO:",
            len(offers)
        )

        offers = offers[
            :MAX_TEST_OFFERS
        ]

        print(
            "W TEŚCIE ANALIZUJĘ:",
            len(offers)
        )

        # ====================================================
        # 2. ANALIZA OFERT
        # ====================================================

        for index, offer in enumerate(
            offers,
            start=1
        ):

            print()
            print("#" * 80)
            print(
                f"OFERTA {index}/{len(offers)}"
            )
            print("#" * 80)

            url = offer.get("url")

            print(
                "TYTUŁ:",
                offer.get("title")
            )

            print(
                "CENA:",
                offer.get("price")
            )

            print(
                "LOKALIZACJA:",
                offer.get("location")
            )

            print(
                "LINK:",
                url
            )

            if not url:
                print(
                    "[ODRZUT] Brak URL"
                )
                continue

            # =================================================
            # 3. OTWIERAMY SZCZEGÓŁY
            # =================================================

            try:

                detail_page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                detail_page.wait_for_timeout(
                    2500
                )

            except Exception as e:

                print(
                    "[ERROR OPEN]",
                    repr(e)
                )

                continue

            # =================================================
            # 4. PEŁNE METADANE FACEBOOKA
            # =================================================

            metadata = extract_detail_metadata(
                detail_page
            )

            if not metadata:

                print(
                    "[ODRZUT] Brak metadanych"
                )

                continue

            if metadata.get("is_sold") is True:

                print(
                    "[ODRZUT] Oferta sprzedana"
                )

                continue

            if metadata.get("is_live") is False:

                print(
                    "[ODRZUT] Oferta nieaktywna"
                )

                continue

            # Cena ze szczegółów jest ważniejsza
            # niż cena z karty wyszukiwania.

            price = metadata.get(
                "price"
            )

            if price is None:
                price = offer.get(
                    "price"
                )

            if price is None:

                print(
                    "[ODRZUT] Brak ceny"
                )

                continue

            # =================================================
            # 5. PARSOWANIE SPRZĘTU
            # =================================================

            description = (
                metadata.get("description")
                or ""
            )

            specs = parse_pc_specs(
                title=metadata.get(
                    "title"
                ),
                description=description,
            )

            print()
            print("=== SPRZĘT ===")

            print(
                "CPU:",
                specs.get("cpu")
            )

            print(
                "GPU:",
                specs.get("gpu")
            )

            print(
                "RAM:",
                specs.get("ram")
            )

            print(
                "DYSKI:",
                specs.get("disks")
            )

            print(
                "PŁYTA:",
                specs.get("motherboard")
            )

            print(
                "PSU:",
                specs.get("psu")
            )

            # =================================================
            # 6. FILTR SPRZĘTOWY
            # =================================================

            ok, reasons = hardware_ok({
                "cpu": specs.get("cpu"),
                "ram": specs.get("ram"),
            })

            if not ok:

                print()
                print(
                    "[ODRZUT SPRZĘTOWY]"
                )

                for reason in reasons:
                    print(
                        "-",
                        reason
                    )

                continue

            print()
            print(
                "[SPRZĘT OK]"
            )

            # =================================================
            # 7. WYCENA V3
            # =================================================

            valuation_input = {
                "cpu":
                    specs.get("cpu"),

                "gpu":
                    specs.get("gpu"),

                "ram":
                    specs.get("ram"),

                "disks":
                    specs.get("disks"),

                "price":
                    price,
            }

            result = estimate_flip_v3(
                valuation_input,
                "LOCAL"
            )

            print()
            print("=== WYCENA V3 ===")

            if not result.get("ok"):

                print(
                    "[ODRZUT WYCENA]"
                )

                print(
                    result.get("reason")
                )

                continue

            print(
                "CENA ZAKUPU:",
                result.get("purchase_price")
            )

            print(
                "SZYBKA SPRZEDAŻ:",
                result.get("quick_sale")
            )

            print(
                "KOSZT CAŁKOWITY:",
                result.get("total_cost")
            )

            print(
                "ZYSK:",
                result.get("profit")
            )

            print(
                "ŹRÓDŁO WYCENY:",
                result.get("valuation_source")
            )

            print(
                "PEWNOŚĆ:",
                result.get("confidence")
            )

            # =================================================
            # 8. DECYZJA
            # =================================================

            profit = result.get(
                "profit",
                -999999
            )

            print()
            print("=== DECYZJA ===")

            if profit >= 500:

                print(
                    "🔥 PRIORYTETOWY FLIP"
                )

            elif profit >= 400:

                print(
                    "✅ FLIP"
                )

            else:

                print(
                    "❌ NIEOPŁACALNE"
                )

        browser.close()

    print()
    print("=" * 80)
    print("FACEBOOK VALUATION TEST ZAKOŃCZONY")
    print("=" * 80)


if __name__ == "__main__":
    main()
