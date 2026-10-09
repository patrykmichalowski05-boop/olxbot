from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

import re


# ============================================================
# DATABASE
# ============================================================

from database import (
    init_db,
    observe_offer,
    mark_analyzed,
    mark_analysis_failure,
)


# ============================================================
# PARSER / FILTERS
# ============================================================

from offer_parser import extract_offer

from filters import hardware_ok, purchase_price_ok


# ============================================================
# VALUATION V3
# ============================================================

from valuation_v3 import (
    estimate_flip_v3,
)


# ============================================================
# AI SPEC RECOVERY
# ============================================================

from spec_recovery import (
    recover_missing_specs,
    missing_specs,
)


# ============================================================
# AI CONDITION ANALYSIS
# ============================================================

from ai_analyzer import (
    analyze_offer,
    apply_ai_adjustment,
)


# ============================================================
# PRICE RESOLVER
# ============================================================

from price_resolver import (
    resolve_offer_price,
)


# ============================================================
# BUNDLE / SETUP
# ============================================================

from bundle_detector import (
    analyze_bundle,
)

from bundle_valuation import (
    apply_bundle_valuation,
)


# ============================================================
# TELEGRAM
# ============================================================

from telegram_notifier import (
    send_flip_alert,
)


# ============================================================
# BROWSER
# ============================================================

from browser_utils import (
    block_heavy_resources,
)


# ============================================================
# DECISION LOG
# ============================================================

from decision_log import (
    init_decision_db,
    log_decision,
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

from scanner_settings import get_int

AI_MIN_PROFIT = 300
FINAL_MIN_PROFIT = 400


# ============================================================
# SAFE DECISION LOG
# ============================================================

def safe_log_decision(
    offer_id,
    details,
    valuation,
    mode,
    offer_url,
    decision,
    reason,
    stage,
):

    try:

        log_decision(
            offer_id=offer_id,
            details=details or {},
            valuation=valuation or {},
            mode=mode,
            offer_url=offer_url,
            decision=decision,
            reason=reason,
            stage=stage,
        )

    except Exception as e:

        print(
            "[DECISION LOG ERROR] "
            f"{e}"
        )


# ============================================================
# OLX ID
# ============================================================

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


# ============================================================
# URL
# ============================================================

def clean_url(url):

    if not url:
        return None

    return url.split("?")[0]


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
# CARD PRICE
# ============================================================

def parse_card_price(text):

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
# AI SPEC RECOVERY
# ============================================================

def recover_specs_if_needed(
    details,
):

    missing = missing_specs(
        details
    )

    if not missing:
        return details

    print()

    print(
        "[SPEC AI] "
        "Brakujące dane: "
        + ", ".join(missing)
    )

    try:

        result = recover_missing_specs(
            details
        )

    except Exception as e:

        print(
            "[SPEC AI ERROR] "
            f"{e}"
        )

        return details

    if not result.get(
        "ok"
    ):

        print(
            "[SPEC AI ERROR] "
            + result.get(
                "reason",
                "Nieznany błąd",
            )
        )

        return details

    recovered = (
        result.get("details")
        or details
    )

    filled = (
        result.get("filled")
        or []
    )

    rejected = (
        result.get("rejected")
        or []
    )

    for item in filled:

        print(
            "[SPEC AI OK] "
            f"{item.get('field')}: "
            f"{item.get('value')} "
            f"| conf="
            f"{item.get('confidence')} "
            f"| dowód="
            f"{item.get('evidence')}"
        )

    for item in rejected:

        print(
            "[SPEC AI ODRZUT] "
            f"{item.get('field')}: "
            f"{item.get('value')} "
            f"| conf="
            f"{item.get('confidence')}"
        )

    recovered[
        "_spec_ai_used"
    ] = bool(filled)

    recovered[
        "_spec_ai_fields"
    ] = [
        item.get("field")
        for item in filled
    ]

    return recovered


# ============================================================
# ANALIZA JEDNEJ OFERTY
# ============================================================

def analyze_candidate(
    detail_page,
    offer_id,
    offer_url,
    card_title,
    card_price,
    mode,
    trigger,
):

    print()

    print(
        "-" * 80
    )

    if trigger == "PRICE_DROP":

        print(
            "[OBNIŻKA CENY] "
            f"{offer_id}"
        )

    else:

        print(
            "[NOWA] "
            f"{offer_id}"
        )

    print(
        f"[{mode}] "
        f"{card_title}"
    )

    print(
        f"CENA FEED: "
        f"{card_price} zł"
    )

    print(
        f"LINK: "
        f"{offer_url}"
    )

    # ========================================================
    # BASE DETAILS
    # ========================================================

    base_details = {
        "title": card_title,
        "price": card_price,
        "_trigger": trigger,
    }

    # ========================================================
    # PARSER
    # ========================================================

    try:

        details = extract_offer(
            detail_page,
            offer_url,
        )

    except Exception as e:

        print(
            "[ERROR PARSER] "
            f"{e}"
        )

        mark_analysis_failure(
            offer_id,
            e,
        )

        safe_log_decision(
            offer_id=offer_id,
            details=base_details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="ERROR",
            reason="PARSER_EXCEPTION",
            stage="PARSER",
        )

        return False

    if not details:

        print(
            "[ERROR PARSER] "
            "Brak danych."
        )

        mark_analysis_failure(
            offer_id,
            "extract_offer returned None",
        )

        safe_log_decision(
            offer_id=offer_id,
            details=base_details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="ERROR",
            reason="PARSER_EMPTY",
            stage="PARSER",
        )

        return False

    details[
        "_trigger"
    ] = trigger

    if not details.get(
        "title"
    ):

        details[
            "title"
        ] = card_title

    # ========================================================
    # PRICE RESOLVER
    # ========================================================

    try:

        price_result = (
            resolve_offer_price(
                detail_page,
                card_price=card_price,
                details=details,
            )
        )

    except Exception as e:

        print(
            "[CENA ERROR] "
            f"Price resolver: {e}"
        )

        price_result = {
            "price": None,
            "source": "ERROR",
        }

    resolved_price = (
        price_result.get(
            "price"
        )
    )

    price_source = (
        price_result.get(
            "source"
        )
    )

    # Maksymalna cena zakupu z panelu Flip Hunter V2.
    # Kontrola po ustaleniu ceny, przed dalsza wycena.
    from scanner_settings import get_int

    budget_limit = get_int("max_purchase_price")

    if budget_limit > 0:
        if resolved_price is None:
            print(
                "[BUDZET OLX] Nieznana cena - "
                "pomijam analize do ponownej obserwacji."
            )
            return False

        if not purchase_price_ok(resolved_price):
            print(
                f"[BUDZET OLX] {resolved_price} zl "
                f"przekracza limit {budget_limit} zl."
            )

            details["price"] = resolved_price

            safe_log_decision(
                offer_id=offer_id,
                details=details,
                valuation={},
                mode=mode,
                offer_url=offer_url,
                decision="REJECT",
                reason="PRICE_OVER_BUDGET",
                stage="PRICE",
            )

            return False

    if resolved_price is not None:

        details[
            "price"
        ] = resolved_price

        details[
            "_price_source"
        ] = price_source

        print(
            "[CENA] "
            f"{resolved_price} zł "
            f"| źródło: "
            f"{price_source}"
        )

    else:

        print(
            "[CENA ERROR] "
            "Nie udało się ustalić ceny."
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="ERROR",
            reason="PRICE_NOT_FOUND",
            stage="PRICE",
        )

        mark_analysis_failure(
            offer_id,
            "PRICE_NOT_FOUND",
        )

        return False

    analyzed_price = (
        details.get(
            "price"
        )
    )

    # ========================================================
    # AI SPEC RECOVERY
    # ========================================================

    details = recover_specs_if_needed(
        details
    )

    # ========================================================
    # BUNDLE DETECTOR
    # ========================================================

    bundle = analyze_bundle(
        details
    )

    details[
        "_bundle"
    ] = bundle

    if bundle.get(
        "is_bundle"
    ):

        print()

        print(
            "[BUNDLE DETECTED]"
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
            "Strong: "
            f"{bundle.get('strong_bundle')}"
        )

        print(
            "Dodatki quick value: "
            f"{bundle.get('accessory_quick_value')} zł"
        )

        for item in (
            bundle.get("items")
            or []
        ):

            print(
                "  + "
                f"{item.get('label')} "
                f"~{item.get('quick_value')} zł "
                f"[{item.get('confidence')}]"
            )

    # ========================================================
    # SPEC PRINT
    # ========================================================

    print()

    print(
        "[SPECYFIKACJA]"
    )

    print(
        "CPU: "
        f"{details.get('cpu')}"
    )

    print(
        "GPU: "
        f"{details.get('gpu')}"
    )

    print(
        "RAM: "
        f"{details.get('ram')}"
    )

    print(
        "DYSKI: "
        f"{details.get('disks')}"
    )

    # ========================================================
    # HARDWARE FILTER
    # ========================================================

    try:

        valid, hardware_reasons = (
            hardware_ok(
                details
            )
        )

    except Exception as e:

        print(
            "[HARDWARE FILTER ERROR] "
            f"{e}"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="ERROR",
            reason="HARDWARE_FILTER_EXCEPTION",
            stage="HARDWARE",
        )

        mark_analysis_failure(
            offer_id,
            e,
        )

        return False

    if not valid:

        print(
            "[ODRZUT SPRZĘTOWY]"
        )

        for item in hardware_reasons:

            print(
                f" - {item}"
            )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason="HARDWARE_FILTER",
            stage="HARDWARE",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    if not details.get(
        "gpu"
    ):

        print(
            "[ODRZUT SPRZĘTOWY] "
            "GPU nierozpoznane."
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason="GPU_UNKNOWN",
            stage="HARDWARE",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    # ========================================================
    # SHIPPING / BUNDLE PICKUP OVERRIDE
    # ========================================================

    bundle_pickup_override = (
        mode == "POLSKA"
        and
        not details.get(
            "shipping"
        )
        and
        bundle.get(
            "strong_bundle"
        )
    )

    details[
        "_bundle_pickup_override"
    ] = bundle_pickup_override

    if (
        mode == "POLSKA"
        and
        not details.get(
            "shipping"
        )
        and
        not bundle_pickup_override
    ):

        print(
            "[ODRZUT POLSKA] "
            "Brak Przesyłki OLX / "
            "Kup teraz"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason="NO_OLX_SHIPPING",
            stage="SHIPPING",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    if bundle_pickup_override:

        print()

        print(
            "[BUNDLE PICKUP OVERRIDE]"
        )

        print(
            "Brak Przesyłki OLX, "
            "ale mocny setup przechodzi "
            "do wyceny."
        )

    # ========================================================
    # VALUATION V3
    # ========================================================

    valuation_mode = (
        "LOCAL"
        if bundle_pickup_override
        else mode
    )

    try:

        valuation = estimate_flip_v3(
            details,
            valuation_mode,
        )

    except Exception as e:

        print(
            "[VALUATION ERROR] "
            f"{e}"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation={},
            mode=mode,
            offer_url=offer_url,
            decision="ERROR",
            reason="VALUATION_EXCEPTION",
            stage="VALUATION",
        )

        mark_analysis_failure(
            offer_id,
            e,
        )

        return False

    if not valuation.get(
        "ok"
    ):

        valuation_reason = (
            valuation.get(
                "reason",
                "Brak wyceny",
            )
        )

        print(
            "[ODRZUT WYCENA] "
            f"{valuation_reason}"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason="VALUATION_FAILED",
            stage="VALUATION",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    # ========================================================
    # BUNDLE VALUATION
    # ========================================================

    valuation = apply_bundle_valuation(
        valuation,
        bundle,
    )

    valuation[
        "bundle_pickup_override"
    ] = bundle_pickup_override

    if valuation.get(
        "bundle_detected"
    ):

        print()

        print(
            "[WYCENA BUNDLE]"
        )

        print(
            "PC quick sale: "
            f"{valuation.get('bundle_pc_quick_sale')} zł"
        )

        print(
            "Dodatki RAW: "
            f"{valuation.get('bundle_accessory_value_raw')} zł"
        )

        print(
            "Dodatki użyte: "
            f"{valuation.get('bundle_accessory_value')} zł"
        )

        print(
            "Bundle quick sale: "
            f"{valuation.get('quick_sale')} zł"
        )

        print(
            "Bundle profit: "
            f"{valuation.get('profit')} zł"
        )

    # ========================================================
    # V3 PRINT
    # ========================================================

    print()

    print(
        "[WYCENA V3]"
    )

    print(
        "Zakup: "
        f"{details.get('price')} zł"
    )

    print(
        "Szybka sprzedaż: "
        f"{valuation.get('quick_sale')} zł"
    )

    print(
        "Koszt razem: "
        f"{valuation.get('total_cost')} zł"
    )

    print(
        "Zysk: "
        f"{valuation.get('profit')} zł"
    )

    print(
        "Źródło: "
        f"{valuation.get('valuation_source')}"
    )

    print(
        "Confidence: "
        f"{valuation.get('confidence')}"
    )

    print(
        "Static: "
        f"{valuation.get('static_quick_sale')} zł"
    )

    print(
        "Exact: "
        f"{valuation.get('exact_samples')} "
        f"| quick="
        f"{valuation.get('exact_quick_sale')}"
    )

    print(
        "Similar same GPU: "
        f"{valuation.get('similar_samples')} "
        f"| quick="
        f"{valuation.get('similar_quick_sale')} "
        f"| similarity="
        f"{valuation.get('similarity')}"
    )

    print(
        "Neighbor market: "
        f"{valuation.get('neighbor_samples')} "
        f"| neighbor GPU="
        f"{valuation.get('neighbor_gpu_samples')} "
        f"| similarity="
        f"{valuation.get('neighbor_similarity')}"
    )

    print(
        "Neighbor quick raw: "
        f"{valuation.get('neighbor_quick_raw')} zł"
    )

    print(
        "Neighbor quick protected: "
        f"{valuation.get('neighbor_quick_protected')} zł"
    )

    print(
        "Neighbor protection: "
        f"{valuation.get('neighbor_protected')}"
    )

    print(
        "Sanity cap: "
        f"{valuation.get('sanity_cap_applied')} "
        f"| limit="
        f"{valuation.get('sanity_cap')}"
    )

    # ========================================================
    # PRE-AI PROFIT
    # ========================================================

    from negotiation_gate import negotiation_candidate

    profit_before_ai = (
        valuation.get(
            "profit"
        )
    )

    if profit_before_ai is None:

        print(
            "[ODRZUT WYCENA] "
            "Brak policzonego zysku."
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason="PROFIT_MISSING",
            stage="PRE_AI",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    if (
        profit_before_ai < get_int('ai_min_profit')
        and not negotiation_candidate(details, valuation)
    ):

        print(
            "[ODRZUT PRZED AI] "
            f"{profit_before_ai} zł "
            f"< {get_int('ai_min_profit')} zł"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason=f"PRE_AI_PROFIT_BELOW_{get_int('ai_min_profit')}",
            stage="PRE_AI",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    # ========================================================
    # AI CONDITION
    # ========================================================

    print()

    print(
        "[AI] "
        "Analizuję stan i ryzyka..."
    )

    try:

        ai_result = analyze_offer(
            details
        )

    except Exception as e:

        ai_result = {
            "ok": False,
            "reason": str(e),
        }

    if ai_result.get(
        "ok"
    ):

        print(
            "[AI] Stan: "
            f"{ai_result.get('condition')}"
        )

        print(
            "[AI] Korekta: "
            f"{ai_result.get('adjustment_percent')}%"
        )

        print(
            "[AI] Confidence: "
            f"{ai_result.get('confidence')}"
        )

        for issue in (
            ai_result.get(
                "issues"
            )
            or []
        ):

            print(
                "[AI RYZYKO] "
                f"{issue}"
            )

        try:

            valuation = apply_ai_adjustment(
                valuation,
                ai_result,
            )

        except Exception as e:

            print(
                "[AI ADJUST ERROR] "
                f"{e}"
            )

    else:

        print(
            "[AI ERROR] "
            + ai_result.get(
                "reason",
                "Nieznany błąd",
            )
        )

        valuation[
            "ai_condition"
        ] = "UNAVAILABLE"

        valuation[
            "ai_adjustment_percent"
        ] = 0

        valuation[
            "ai_confidence"
        ] = 0

        valuation[
            "ai_issues"
        ] = []

        valuation[
            "ai_missing_info"
        ] = []

        valuation[
            "ai_summary"
        ] = (
            "Analiza AI niedostępna."
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print(
        "[WYCENA FINALNA]"
    )

    print(
        "Szybka sprzedaż: "
        f"{valuation.get('quick_sale')} zł"
    )

    print(
        "Koszt razem: "
        f"{valuation.get('total_cost')} zł"
    )

    print(
        "Zysk: "
        f"{valuation.get('profit')} zł"
    )

    final_profit = (
        valuation.get(
            "profit"
        )
    )

    if (
        final_profit is None
        or
        (
            final_profit < get_int('final_min_profit')
            and not negotiation_candidate(details, valuation)
        )
    ):

        print(
            "[ODRZUT FINALNY] "
            f"{final_profit} zł "
            f"< {get_int('final_min_profit')} zł"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="REJECT",
            reason=f"FINAL_PROFIT_BELOW_{get_int('final_min_profit')}",
            stage="FINAL",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
        )

        return False

    # ========================================================
    # ACCEPT
    # ========================================================

    print()

    print(
        "#" * 80
    )

    if valuation.get(
        "bundle_detected"
    ):

        print(
            "BUNDLE / SETUP"
        )

    if valuation.get(
        "hot"
    ):

        print(
            "GORĄCA OKAZJA"
        )

    else:

        print(
            "DOBRY FLIP"
        )

    if bundle_pickup_override:

        print(
            "ODBIÓR OSOBISTY — "
            "BUNDLE OVERRIDE"
        )

    if trigger == "PRICE_DROP":

        print(
            "PO OBNIŻCE CENY"
        )

    if details.get(
        "_spec_ai_used"
    ):

        print(
            "SPECYFIKACJA "
            "UZUPEŁNIONA PRZEZ AI"
        )

    print(
        "#" * 80
    )

    print(
        "CENA:       "
        f"{details.get('price')} zł"
    )

    print(
        "CPU:        "
        f"{details.get('cpu')}"
    )

    print(
        "GPU:        "
        f"{details.get('gpu')}"
    )

    print(
        "RAM:        "
        f"{details.get('ram')} GB"
    )

    if valuation.get(
        "bundle_detected"
    ):

        print(
            "PC VALUE:   "
            f"{valuation.get('bundle_pc_quick_sale')} zł"
        )

        print(
            "DODATKI:    "
            f"{valuation.get('bundle_accessory_value')} zł"
        )

    print(
        "ODSPRZEDAŻ: "
        f"{valuation.get('quick_sale')} zł"
    )

    print(
        "ZYSK:       "
        f"{valuation.get('profit')} zł"
    )

    print(
        "LINK:       "
        f"{offer_url}"
    )

    print(
        "#" * 80
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    try:

        telegram_ok = send_flip_alert(
            details,
            valuation,
            mode,
            offer_url,
            return_status=True,
        )

    except Exception as e:

        telegram_ok = False

        print(
            "[TELEGRAM EXCEPTION] "
            f"{e}"
        )

    if telegram_ok == "SENT":

        print(
            "[ALERT] Telegram OK"
        )

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="ACCEPT",
            reason="PROFIT_OR_NEGOTIATION_OK",
            stage="FINAL",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
            alerted=True,
        )

        return True

    if telegram_ok == "SUPPRESSED":
        print("[ALERT] SUPPRESSED - bez wysylki")

        safe_log_decision(
            offer_id=offer_id,
            details=details,
            valuation=valuation,
            mode=mode,
            offer_url=offer_url,
            decision="SUPPRESSED",
            reason="NOTIFICATION_SUPPRESSED",
            stage="ALERT",
        )

        mark_analyzed(
            offer_id,
            analyzed_price,
            alerted=False,
        )

        return False

    print(
        "[ALERT ERROR] "
        "Telegram nie wysłał."
    )

    safe_log_decision(
        offer_id=offer_id,
        details=details,
        valuation=valuation,
        mode=mode,
        offer_url=offer_url,
        decision="ERROR",
        reason="TELEGRAM_FAILED",
        stage="ALERT",
    )

    return False


# ============================================================
# FEED SCAN
# ============================================================

def scan_feed(
    search_page,
    detail_page,
    mode,
    url,
):

    print()

    print(
        "=" * 80
    )

    print(
        "SKAN: KÓRNIK + 30 KM"
        if mode == "LOCAL"
        else
        "SKAN: CAŁA POLSKA"
    )

    print(
        "=" * 80
    )

    try:

        search_page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        search_page.wait_for_selector(
            '[data-cy="l-card"]',
            timeout=10000,
        )

    except Exception as e:

        print(
            "[ERROR FEED] "
            f"{e}"
        )

        return {
            "new": 0,
            "drops": 0,
            "flips": 0,
        }

    cards = search_page.locator(
        '[data-cy="l-card"]'
    )

    count = min(
        cards.count(),
        MAX_CARDS,
    )

    print(
        "Ofert w feedzie: "
        f"{count}"
    )

    processed_ids = set()

    new_count = 0
    drop_count = 0
    flip_count = 0

    for i in range(
        count
    ):

        try:

            card = cards.nth(i)

            card_text = (
                card.inner_text()
                .strip()
            )

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

            if offer_id in processed_ids:
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
                else "Brak tytułu"
            )

            card_price = (
                parse_card_price(
                    card_text
                )
            )

            observation = observe_offer(
                offer_id,
                card_title,
                card_price,
                offer_url,
            )

            if observation[
                "is_new"
            ]:

                new_count += 1

            if (
                observation[
                    "price_drop"
                ]
                and
                not observation[
                    "is_new"
                ]
            ):

                drop_count += 1

                print()

                print(
                    "[PRICE DROP] "
                    f"{offer_id}: "
                    f"{observation['previous_price']} zł"
                    " -> "
                    f"{observation['current_price']} zł"
                )

            if not observation[
                "should_analyze"
            ]:

                continue

            accepted = analyze_candidate(
                detail_page=detail_page,
                offer_id=offer_id,
                offer_url=offer_url,
                card_title=card_title,
                card_price=card_price,
                mode=mode,
                trigger=observation[
                    "reason"
                ],
            )

            if accepted:

                flip_count += 1

        except Exception as e:

            print(
                f"[ERROR KARTA {i}] "
                f"{e}"
            )

    return {
        "new": new_count,
        "drops": drop_count,
        "flips": flip_count,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()
    init_decision_db()

    totals = {
        "new": 0,
        "drops": 0,
        "flips": 0,
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
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

        local = scan_feed(
            search_page=search_page,
            detail_page=detail_page,
            mode="LOCAL",
            url=LOCAL_URL,
        )

        for key in totals:

            totals[key] += (
                local[key]
            )

        national = scan_feed(
            search_page=search_page,
            detail_page=detail_page,
            mode="POLSKA",
            url=POLSKA_URL,
        )

        for key in totals:

            totals[key] += (
                national[key]
            )

        browser.close()

    print()

    print(
        "=" * 80
    )

    print(
        "SKAN GOTOWY | "
        f"nowe: "
        f"{totals['new']} | "
        f"obniżki: "
        f"{totals['drops']} | "
        f"flipy: "
        f"{totals['flips']}"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
