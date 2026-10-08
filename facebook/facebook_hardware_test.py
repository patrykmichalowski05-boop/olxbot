from playwright.sync_api import sync_playwright

from facebook.facebook_config import SEARCHES
from facebook.facebook_scanner import scan_query
from facebook.facebook_detail_parser import extract_detail_metadata
from facebook.facebook_specs_parser import parse_pc_specs

from filters import hardware_ok


MAX_TEST_OFFERS = 5


def main():

    print("=" * 80)
    print("FACEBOOK HARDWARE TEST")
    print("=" * 80)

    query = SEARCHES[0]

    print()
    print("Fraza wyszukiwania:")
    print(query)

    with sync_playwright() as p:

        # ----------------------------------------------------
        # URUCHAMIAMY PRZEGLĄDARKĘ
        # ----------------------------------------------------

        browser = p.chromium.launch(
            headless=True
        )

        # ----------------------------------------------------
        # STRONA WYNIKÓW WYSZUKIWANIA
        # ----------------------------------------------------

        search_page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        # ----------------------------------------------------
        # OSOBNA STRONA DO OTWIERANIA OGŁOSZEŃ
        # ----------------------------------------------------

        detail_page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        print()
        print("=" * 80)
        print("KROK 1: POBIERAM LISTĘ OFERT")
        print("=" * 80)

        offers = scan_query(
            search_page,
            query
        )

        print()
        print(
            "Ofert pobranych z Marketplace:",
            len(offers)
        )

        # ----------------------------------------------------
        # TESTUJEMY TYLKO PIERWSZE KILKA
        # ----------------------------------------------------

        offers = offers[
            :MAX_TEST_OFFERS
        ]

        print(
            "Ofert analizowanych w teście:",
            len(offers)
        )

        # ----------------------------------------------------
        # ANALIZA KAŻDEJ OFERTY
        # ----------------------------------------------------

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

            print(
                "CENA Z LISTY:",
                offer.get("price")
            )

            print(
                "TYTUŁ Z LISTY:",
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

            url = offer.get("url")

            if not url:
                print(
                    "[ODRZUT] Brak URL."
                )
                continue

            # ------------------------------------------------
            # OTWIERAMY PEŁNE OGŁOSZENIE
            # ------------------------------------------------

            print()
            print(
                "[OTWIERAM SZCZEGÓŁY]"
            )

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

            # ------------------------------------------------
            # POBIERAMY PEŁNE DANE Z HTML FACEBOOKA
            # ------------------------------------------------

            metadata = extract_detail_metadata(
                detail_page
            )

            if not metadata:

                print(
                    "[ODRZUT] Nie udało się "
                    "odczytać metadanych."
                )

                continue

            print()
            print("=== METADANE ===")

            print(
                "TYTUŁ:",
                metadata.get("title")
            )

            print(
                "CENA:",
                metadata.get("price")
            )

            print(
                "STARA CENA:",
                metadata.get("old_price")
            )

            print(
                "LOKALIZACJA:",
                metadata.get("location")
            )

            print(
                "AKTYWNA:",
                metadata.get("is_live")
            )

            print(
                "SPRZEDANA:",
                metadata.get("is_sold")
            )

            description = (
                metadata.get("description")
                or ""
            )

            print(
                "DŁUGOŚĆ OPISU:",
                len(description)
            )

            # ------------------------------------------------
            # PARSUJEMY PODZESPOŁY
            # ------------------------------------------------

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
                specs.get(
                    "motherboard"
                )
            )

            print(
                "PSU:",
                specs.get("psu")
            )

            # ------------------------------------------------
            # FILTR SPRZĘTOWY
            # ------------------------------------------------

            filter_data = {
                "cpu":
                    specs.get("cpu"),

                "ram":
                    specs.get("ram"),
            }

            ok, reasons = hardware_ok(
                filter_data
            )

            print()
            print("=== FILTR ===")

            if not ok:

                print(
                    "[ODRZUT SPRZĘTOWY]"
                )

                for reason in reasons:
                    print(
                        "-",
                        reason
                    )

                continue

            print(
                "[SPRZĘT OK]"
            )

            print(
                "Oferta przechodzi "
                "minimalne wymagania."
            )

        # ----------------------------------------------------
        # KONIEC
        # ----------------------------------------------------

        browser.close()

    print()
    print("=" * 80)
    print("TEST ZAKOŃCZONY")
    print("=" * 80)


if __name__ == "__main__":
    main()
