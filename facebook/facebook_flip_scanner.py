import argparse
from datetime import datetime

from playwright.sync_api import sync_playwright

from facebook.facebook_config import SEARCHES
from facebook.facebook_scanner import scan_query
from facebook.facebook_detail_parser import extract_detail_metadata
from facebook.facebook_specs_parser import parse_pc_specs

from facebook.facebook_seen import (
    init_db,
    observe_offer,
    mark_analyzed,
    mark_alert_sent,
    ensure_alert_columns,
    get_offer,
)

from filters import hardware_ok
from valuation_v3 import estimate_flip_v3

from telegram_notifier import (
    send_flip_alert,
)


MIN_PROFIT = 400
PRIORITY_PROFIT = 500


def send_facebook_flip_alert(
    offer,
    metadata,
    specs,
    valuation,
    url,
):
    """
    Wysyła ofertę Facebook Marketplace przez
    ten sam notifier Telegram co OLX.

    Cena zakupu pochodzi z Facebooka.
    Wycena sprzedaży pochodzi z valuation_v3,
    którego rynek referencyjny to OLX market.db.
    """

    price = metadata.get("price")

    if price is None:
        price = offer.get("price")

    title = (
        metadata.get("title")
        or offer.get("title")
        or "Komputer"
    )

    details = {
        "title":
            f"[FB Marketplace] {title}",

        "price":
            price,

        "cpu":
            specs.get("cpu"),

        "gpu":
            specs.get("gpu"),

        "ram":
            specs.get("ram"),

        "disks":
            specs.get("disks"),

        # Facebook lokalnie = bez kosztu
        # wysyłki OLX.
        "shipping":
            False,

        # Informacje dodatkowe zostawiamy
        # również w słowniku pod przyszłą
        # wersję notifiera.
        "location":
            metadata.get("location")
            or offer.get("location"),

        "motherboard":
            specs.get("motherboard"),

        "psu":
            specs.get("psu"),

        "_source":
            "FACEBOOK_MARKETPLACE",

        "_trigger":
            "NEW",
    }

    try:
        status = send_flip_alert(
            details,
            valuation,
            "LOCAL",
            url,
            return_status=True,
        )

    except Exception as e:
        print("[TELEGRAM EXCEPTION]", repr(e))
        return "ERROR"

    if status == "SENT":
        print("[ALERT] Facebook -> Telegram OK")
    elif status == "SUPPRESSED":
        print("[ALERT] Facebook -> SUPPRESSED")
    else:
        print("[ALERT] Facebook -> ERROR")

    return status


def format_creation_time(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(
            timestamp
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        return None


def analyze_offer(
    detail_page,
    offer,
    listing_id,
    dry_run=False,
):

    url = offer.get("url")

    # FB_INCOMPLETE_COOLDOWN_V1
    from facebook_incomplete_cooldown import (
        cooldown_remaining,
        note_incomplete,
        clear_incomplete,
    )

    if not dry_run:
        remaining = cooldown_remaining(
            listing_id,
            offer.get("title"),
            offer.get("price"),
        )

        if remaining > 0:
            print(
                "[FB COOLDOWN]",
                listing_id,
                "- ponowna analiza za",
                round(remaining / 3600, 1),
                "h",
            )
            return

    print()
    print("=" * 80)
    print("[ANALIZA]")
    print("=" * 80)

    print(
        "TYTUŁ:",
        offer.get("title")
    )

    print(
        "CENA KARTY:",
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

    # ========================================================
    # OTWIERAMY SZCZEGÓŁY
    # ========================================================

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

        # NIE zaznaczamy analyzed.
        # Dzięki temu następny skan spróbuje ponownie.
        return

    # ========================================================
    # METADANE FACEBOOKA
    # ========================================================

    # VERIFIED_FACEBOOK_METADATA_V1
    try:
        metadata = extract_detail_metadata(detail_page)
    except Exception as exc:
        print("[BŁĄD METADANYCH]", repr(exc))
        return

    if not metadata:
        print("[PONOWIMY] Brak metadanych właściwej oferty.")
        return

    if str(metadata.get("listing_id")) != str(listing_id):
        print("[PONOWIMY] ID szczegółów nie zgadza się z ID oferty.")
        return

    if metadata.get("is_sold") is True:
        print("[ODRZUT] Oferta sprzedana.")
        mark_analyzed(listing_id)
        return

    if metadata.get("is_live") is False:
        print("[ODRZUT] Oferta nieaktywna.")
        mark_analyzed(listing_id)
        return

    if (
        metadata.get("is_live") is not True
        or metadata.get("is_sold") is not False
    ):
        print("[PONOWIMY] Brak potwierdzonego statusu oferty.")
        return

    currency = metadata.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        print("[PONOWIMY] Brak waluty. Nie zakładam PLN.")
        return

    currency = currency.strip().upper()
    if currency != "PLN":
        print("[ODRZUT] Waluta:", currency)
        mark_analyzed(listing_id)
        return

    price = metadata.get("price")

    import math
    if (
        isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(price)
        or price <= 0
    ):
        print("[PONOWIMY] Brak poprawnej ceny w szczegółach.")
        return

    print()
    print("ID POTWIERDZONE:", listing_id)
    print("WALUTA:", currency)
    print("=== FACEBOOK DETAIL ===")

    print(
        "CENA:",
        price
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
        "DODANO:",
        format_creation_time(
            metadata.get(
                "creation_time"
            )
        )
    )

    # ========================================================
    # PARSER SPRZĘTU
    # ========================================================

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

    # SKIP_LAPTOP_VALUATION_V1
    import re

    title_for_type = metadata.get("title") or offer.get("title") or ""
    cpu_for_type = specs.get("cpu") or ""

    laptop_title = re.search(
        r"\b(?:laptop\w*|notebook\w*|macbook\w*|"
        r"chromebook\w*|netbook\w*)\b",
        title_for_type,
        re.I,
    )

    mobile_cpu = re.search(
        r"\d(?:HX|HS|HK|HQ|H|U|Y|M|MQ|MX)\b",
        cpu_for_type,
        re.I,
    )

    if laptop_title or mobile_cpu:
        reason = (
            "tytuł wskazuje laptop"
            if laptop_title
            else "procesor mobilny: " + cpu_for_type
        )
        print("[POMIJAM WYCENĘ PC]", reason)
        print("Ten sprzęt wymaga osobnego silnika wyceny laptopów.")
        mark_analyzed(listing_id)
        return


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

    # ========================================================
    # BRAKUJĄCE DANE
    # ========================================================

    missing = []

    if not specs.get("cpu"):
        missing.append("CPU")

    if not specs.get("gpu"):
        missing.append("GPU")

    if specs.get("ram") is None:
        missing.append("RAM")

    if missing:

        if not dry_run:
            note_incomplete(
                listing_id,
                offer.get("title"),
                offer.get("price"),
                missing,
            )

        print()
        print(
            "[BRAK DANYCH]",
            ", ".join(missing)
        )

        print(
            "Nie oznaczam jako przeanalizowane."
        )

        print(
            "Bot spróbuje ponownie przy "
            "kolejnym skanie."
        )

        return

    # ========================================================
    # FILTR SPRZĘTOWY
    # ========================================================
    if not dry_run:
        clear_incomplete(listing_id)


    ok, reasons = hardware_ok({
        "cpu":
            specs.get("cpu"),

        "ram":
            specs.get("ram"),
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

        # To jest deterministyczny odrzut.
        # Np. i5-7400 albo RAM 8 GB.
        mark_analyzed(
            listing_id
        )

        return

    print()
    print(
        "[SPRZĘT OK]"
    )

    # ========================================================
    # WYCENA V3
    # ========================================================

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

    print()
    print("RYNEK REFERENCYJNY: OLX")

    result = estimate_flip_v3(
        valuation_input,
        "LOCAL"
    )

    if not result.get("ok"):

        print()
        print(
            "[ODRZUT WYCENA]"
        )

        print(
            result.get("reason")
        )

        # Jeśli nie znamy wartości komponentu,
        # zostawiamy ofertę do ponownej analizy
        # po rozszerzeniu tabel wycen.
        return

    quick_sale = result.get(
        "quick_sale"
    )

    profit = result.get(
        "profit"
    )

    print()
    print("=== WYCENA V3 ===")

    print(
        "CENA ZAKUPU:",
        price,
        "zł"
    )

    print(
        "SZYBKA SPRZEDAŻ:",
        quick_sale,
        "zł"
    )

    print(
        "KOSZT CAŁKOWITY:",
        result.get(
            "total_cost"
        ),
        "zł"
    )

    print(
        "ZYSK:",
        profit,
        "zł"
    )

    print(
        "ŹRÓDŁO:",
        result.get(
            "valuation_source"
        )
    )

    print(
        "PEWNOŚĆ:",
        result.get(
            "confidence"
        )
    )

    # ========================================================
    # DECYZJA / TELEGRAM / PAMIĘĆ ALERTU
    # ========================================================

    print()
    print("=== DECYZJA ===")

    # --------------------------------------------------------
    # NIEOPŁACALNE
    # --------------------------------------------------------

    if profit < MIN_PROFIT:

        print(
            "❌ NIEOPŁACALNE"
        )

        print(
            "Zysk poniżej",
            MIN_PROFIT,
            "zł"
        )

        # Oferta została poprawnie przeanalizowana.
        # Nie ma powodu analizować jej ponownie,
        # dopóki nie spadnie cena.
        mark_analyzed(
            listing_id,
            profit=profit,
            quick_sale=quick_sale,
        )

        return

    # --------------------------------------------------------
    # OFERTA SPEŁNIA PRÓG FLIPA
    # --------------------------------------------------------

    if profit >= PRIORITY_PROFIT:

        print()
        print(
            "🔥🔥 PRIORYTETOWY FLIP"
        )

    else:

        print()
        print(
            "✅ FLIP"
        )

    print(
        "ZYSK:",
        profit,
        "zł"
    )

    print(
        "LINK:",
        url
    )

    # --------------------------------------------------------
    # SPRAWDZAMY HISTORIĘ ALERTÓW
    # --------------------------------------------------------

    db_offer = get_offer(
        listing_id
    ) or {}

    alert_sent = bool(
        db_offer.get(
            "alert_sent",
            0
        )
    )

    last_alert_price = db_offer.get(
        "last_alert_price"
    )

    last_alert_profit = db_offer.get(
        "last_alert_profit"
    )

    should_send_alert = False
    alert_reason = None

    # --------------------------------------------------------
    # PIERWSZY ALERT
    # --------------------------------------------------------

    if not alert_sent:

        should_send_alert = True
        alert_reason = "FIRST_ALERT"

    # --------------------------------------------------------
    # PONOWNY ALERT PO ISTOTNEJ OBNIŻCE
    # --------------------------------------------------------

    else:

        price_drop_since_alert = 0

        if (
            last_alert_price is not None
            and
            price is not None
        ):
            price_drop_since_alert = (
                last_alert_price
                -
                price
            )

        profit_gain_since_alert = 0

        if (
            last_alert_profit is not None
            and
            profit is not None
        ):
            profit_gain_since_alert = (
                profit
                -
                last_alert_profit
            )

        # Alert ponownie dopiero wtedy, gdy:
        # - cena spadła łącznie min. 150 zł od
        #   ostatniego alertu
        #
        # Dzięki temu obniżka np. 20 zł nie spamuje
        # Telegrama, ale kilka kolejnych obniżek
        # może łącznie wywołać nowy alert.

        if (
            price_drop_since_alert >= 150
        ):

            should_send_alert = True
            alert_reason = "PRICE_DROP"

            print()
            print(
                "[PONOWNY ALERT]"
            )

            print(
                "Cena od ostatniego alertu:",
                last_alert_price,
                "->",
                price
            )

            print(
                "Zysk od ostatniego alertu:",
                last_alert_profit,
                "->",
                profit
            )

        else:

            print()
            print(
                "[ALERT JUŻ BYŁ]"
            )

            print(
                "Nie wysyłam duplikatu."
            )

    # --------------------------------------------------------
    # BRAK NOWEGO ALERTU
    # --------------------------------------------------------

    if not should_send_alert:

        mark_analyzed(
            listing_id,
            profit=profit,
            quick_sale=quick_sale,
        )

        return

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    print()
    print(
        "[TELEGRAM]",
        alert_reason
    )

    if dry_run:

        print()
        print(
            "[DRY RUN] Telegram NIE został wysłany."
        )

        telegram_ok = True

    else:

        telegram_ok = send_facebook_flip_alert(
            offer=offer,
            metadata=metadata,
            specs=specs,
            valuation=result,
            url=url,
        )

    # --------------------------------------------------------
    # TELEGRAM OK
    # --------------------------------------------------------

    if telegram_ok == "SENT" or (dry_run and telegram_ok is True):

        if not dry_run:

            mark_alert_sent(
                listing_id,
                price=price,
                profit=profit,
            )

        mark_analyzed(
            listing_id,
            profit=profit,
            quick_sale=quick_sale,
        )

        print()
        print(
            "[ALERT ZAPISANY W DB]"
        )

        return

    if telegram_ok == "SUPPRESSED":
        print("[FACEBOOK] SUPPRESSED - bez wysylki")
        mark_analyzed(
            listing_id,
            profit=profit,
            quick_sale=quick_sale,
        )
        return

    # --------------------------------------------------------
    # TELEGRAM NIEUDANY
    # --------------------------------------------------------

    print()
    print(
        "[ALERT NIEZAPISANY]"
    )

    print(
        "Telegram nie potwierdził wysłania."
    )

    print(
        "Oferta pozostaje do ponownej analizy "
        "w następnym skanie."
    )

    # Celowo NIE wywołujemy tutaj mark_analyzed().
    # Następny skan spróbuje ponownie.



# ISOLATED_DRY_RUN_V1
from contextlib import contextmanager


@contextmanager
def isolated_dry_run(enabled):
    if not enabled:
        yield
        return

    import sqlite3
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from facebook import facebook_seen

    original = facebook_seen.DB_PATH

    with TemporaryDirectory(prefix="facebook-test-") as directory:
        temporary = Path(directory) / "facebook_seen.db"

        if Path(original).exists():
            uri = Path(original).resolve().as_uri() + "?mode=ro"
            src = sqlite3.connect(uri, uri=True)
            try:
                dst = sqlite3.connect(temporary)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()

        facebook_seen.DB_PATH = temporary
        print("[DRY RUN] Używam tymczasowej kopii bazy Facebooka.")

        try:
            yield
        finally:
            facebook_seen.DB_PATH = original


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "Zapisuje istniejące oferty jako znane "
            "bez pełnej analizy."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Analizuje i wycenia oferty, "
            "ale nie wysyła Telegrama."
        ),
    )

    args = parser.parse_args()
    with isolated_dry_run(args.dry_run):

        # ========================================================
        # BAZA
        # ========================================================

        init_db()
        ensure_alert_columns()

        print()
        print("=" * 80)

        if args.bootstrap:
            print(
                "FACEBOOK BOOTSTRAP"
            )
        else:
            print(
                "FACEBOOK FLIP SCANNER"
            )

        print("=" * 80)

        totals = {
            "cards": 0,
            "new": 0,
            "known": 0,
            "price_drops": 0,
            "analyzed": 0,
        }

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
            # WSZYSTKIE FRAZY WYSZUKIWANIA
            # ====================================================

            for query in SEARCHES:

                print()
                print("#" * 80)
                print(
                    "SZUKAM:",
                    query
                )
                print("#" * 80)

                try:

                    offers = scan_query(
                        search_page,
                        query
                    )

                except Exception as e:

                    print(
                        "[ERROR SEARCH]",
                        repr(e)
                    )

                    continue

                for offer in offers:

                    totals["cards"] += 1

                    state = observe_offer(
                        url=offer.get("url"),
                        title=offer.get("title"),
                        price=offer.get("price"),
                        old_price=offer.get(
                            "old_price"
                        ),
                        location=offer.get(
                            "location"
                        ),
                    )

                    if not state.get("ok"):

                        print(
                            "[BŁĄD DB]",
                            state.get("reason")
                        )

                        continue

                    listing_id = state.get(
                        "listing_id"
                    )

                    # ============================================
                    # BOOTSTRAP
                    # ============================================

                    if args.bootstrap:

                        if state.get("new"):
                            totals["new"] += 1
                        else:
                            totals["known"] += 1

                        continue

                    # ============================================
                    # NOWA OFERTA
                    # ============================================

                    if state.get("new"):

                        totals["new"] += 1

                        print()
                        print(
                            "[NOWA]",
                            listing_id
                        )

                        analyze_offer(
                            detail_page,
                            offer,
                            listing_id,
                            dry_run=args.dry_run,
                        )

                        totals["analyzed"] += 1

                        continue

                    # ============================================
                    # OFERTA JUŻ ZNANA
                    # ============================================

                    totals["known"] += 1

                    previous_price = state.get(
                        "previous_price"
                    )

                    current_price = offer.get(
                        "price"
                    )

                    price_drop = (
                        previous_price is not None
                        and
                        current_price is not None
                        and
                        current_price < previous_price
                    )

                    # ============================================
                    # OBNIŻKA CENY
                    # ============================================

                    if price_drop:

                        totals[
                            "price_drops"
                        ] += 1

                        print()
                        print(
                            "[OBNIŻKA]",
                            listing_id,
                            previous_price,
                            "->",
                            current_price,
                        )

                        analyze_offer(
                            detail_page,
                            offer,
                            listing_id,
                            dry_run=args.dry_run,
                        )

                        totals["analyzed"] += 1

                        continue

                    # ============================================
                    # NIEUDANA WCZEŚNIEJSZA ANALIZA
                    # ============================================

                    if not state.get(
                        "analyzed",
                        False
                    ):

                        print()
                        print(
                            "[PONOWNA ANALIZA]",
                            listing_id
                        )

                        analyze_offer(
                            detail_page,
                            offer,
                            listing_id,
                            dry_run=args.dry_run,
                        )

                        totals["analyzed"] += 1

                        continue

                    # ============================================
                    # ZWYKŁA STARA OFERTA
                    # ============================================

                    print(
                        "[ZNANA]",
                        listing_id,
                        "-> pomijam"
                    )

            browser.close()

        print()
        print("=" * 80)
        print("FACEBOOK SKAN GOTOWY")

        print(
            "KARTY:",
            totals["cards"]
        )

        print(
            "NOWE:",
            totals["new"]
        )

        print(
            "ZNANE:",
            totals["known"]
        )

        print(
            "OBNIŻKI:",
            totals["price_drops"]
        )

        print(
            "ANALIZOWANE:",
            totals["analyzed"]
        )

        print("=" * 80)


if __name__ == "__main__":
    main()
