import html
import os
import math

import requests

from dotenv import load_dotenv

from deal_action import (
    calculate_action,
)

from offer_snapshot import save_snapshot

from watchlist import (
    upsert_watch,
    promote_if_watched,
)

from alert_dedupe import (
    already_sent,
    record_alert,
)


load_dotenv(
    "/opt/olx-bot/.env"
)


BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)


# ============================================================
# BASIC HELPERS
# ============================================================

def esc(value):

    if value is None:
        return "brak"

    return html.escape(
        str(value)
    )


def to_float(
    value,
    default=None,
):

    try:

        if value is None:
            return default

        return float(value)

    except Exception:

        return default


def money(value):

    number = to_float(
        value
    )

    if number is None:
        return "brak"

    number = int(
        round(number)
    )

    return (
        f"{number:,}"
        .replace(",", " ")
        + " zł"
    )


def percent(value):

    number = to_float(
        value
    )

    if number is None:
        return "brak"

    return (
        f"{number:.1f}%"
        .replace(".0%", "%")
    )


def floor_50(value):

    number = to_float(
        value
    )

    if number is None:
        return None

    if number <= 0:
        return None

    return int(
        math.floor(
            number / 50
        )
        * 50
    )


def safe_list(value):

    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple)
    ):

        return [
            item
            for item in value
            if item
        ]

    return [
        value
    ]


# ============================================================
# TRANSLATIONS
# ============================================================

def translate_confidence(value):

    value = str(
        value or ""
    ).upper()

    translations = {
        "VERY_LOW":
            "bardzo niska",

        "LOW":
            "niska",

        "MEDIUM":
            "średnia",

        "HIGH":
            "wysoka",

        "VERY_HIGH":
            "bardzo wysoka",

        "BARDZO NISKI":
            "bardzo niska",

        "NISKI":
            "niska",

        "ŚREDNI":
            "średnia",

        "WYSOKI":
            "wysoka",
    }

    return translations.get(
        value,
        value.lower()
        if value
        else "brak"
    )


def translate_condition(value):

    value = str(
        value or ""
    ).lower()

    translations = {
        "excellent":
            "bardzo dobry",

        "very_good":
            "bardzo dobry",

        "good":
            "dobry",

        "average":
            "przeciętny",

        "fair":
            "przeciętny",

        "risky":
            "ryzykowny",

        "bad":
            "zły",

        "poor":
            "zły",

        "unavailable":
            "brak analizy",
    }

    return translations.get(
        value,
        value
        if value
        else "brak"
    )


def translate_mode(value):

    value = str(
        value or ""
    ).upper()

    if value == "LOCAL":
        return "Kórnik + okolica"

    if value == "POLSKA":
        return "Cała Polska"

    return (
        value
        or "brak"
    )


def translate_trigger(value):

    value = str(
        value or ""
    ).upper()

    translations = {
        "NEW":
            "Nowe ogłoszenie",

        "PRICE_DROP":
            "Obniżka ceny",

        "BUNDLE_DISCOVERY":
            "Wykryty zestaw / setup",

        "BUNDLE_PRICE_DROP":
            "Obniżka ceny zestawu",

        "TEST_QUEUE":
            "Test",
    }

    return translations.get(
        value,
        value
        or "brak"
    )


def translate_source(value):

    value = str(
        value or ""
    ).upper()

    translations = {
        "STATIC":
            "wycena statyczna",

        "MARKET":
            "dane rynkowe",

        "MARKET+STATIC":
            "rynek + statyczna",

        "MARKET+SIMILAR+STATIC":
            "rynek + podobne + statyczna",

        "NEIGHBOR+STATIC":
            "podobne GPU + statyczna",

        "LOW_EXACT+MARKET_V3":
            "mało identycznych + rynek",

        "MARKET_V3":
            "dane rynkowe V3",
    }

    return translations.get(
        value,
        value
        or "brak"
    )


# ============================================================
# SPEC HELPERS
# ============================================================

def disk_text(disks):

    if not disks:
        return "brak danych"

    if isinstance(
        disks,
        (list, tuple)
    ):

        return ", ".join(
            esc(x)
            for x in disks
        )

    return esc(
        disks
    )


def ram_text(value):

    if value is None:
        return "brak"

    text = str(
        value
    )

    if "gb" in text.lower():
        return esc(
            text
        )

    return (
        esc(text)
        + " GB"
    )


# ============================================================
# MARKET SAMPLES
# ============================================================

def sample_count(
    valuation,
):

    values = []

    for key in [
        "exact_samples",
        "similar_samples",
        "neighbor_samples",
        "market_samples",
    ]:

        value = valuation.get(
            key
        )

        number = to_float(
            value
        )

        if number is not None:

            values.append(
                int(number)
            )

    if not values:
        return 0

    # Nie sumujemy wszystkich pól,
    # bo część może opisywać te same dane.
    return max(
        values
    )


# ============================================================
# DEAL SCORE
# ============================================================

def calculate_deal_score(
    details,
    valuation,
    mode,
):

    profit = to_float(
        valuation.get(
            "profit"
        ),
        0,
    )

    total_cost = to_float(
        valuation.get(
            "total_cost"
        ),
        0,
    )

    purchase_price = to_float(
        details.get(
            "price"
        ),
        0,
    )

    quick_sale = to_float(
        valuation.get(
            "quick_sale"
        ),
        0,
    )

    confidence = str(
        valuation.get(
            "confidence"
        )
        or ""
    ).upper()

    # Normalizacja pewnosci wyceny PL / EN.
    confidence_aliases = {
        "ŚREDNI": "MEDIUM",
        "SREDNI": "MEDIUM",
        "WYSOKI": "HIGH",
        "BARDZO WYSOKI": "VERY_HIGH",
        "BARDZO_WYSOKI": "VERY_HIGH",
        "NISKI": "LOW",
        "BARDZO NISKI": "VERY_LOW",
        "BARDZO_NISKI": "VERY_LOW",
    }

    confidence = confidence_aliases.get(
        confidence,
        confidence
    )

    hot = bool(
        valuation.get(
            "hot"
        )
    )

    bundle = bool(
        valuation.get(
            "bundle_detected"
        )
    )

    strong_bundle = bool(
        valuation.get(
            "bundle_strong"
        )
    )

    ai_condition = str(
        valuation.get(
            "ai_condition"
        )
        or ""
    ).lower()

    issues = safe_list(
        valuation.get(
            "ai_issues"
        )
    )

    missing = safe_list(
        valuation.get(
            "ai_missing_info"
        )
    )

    samples = sample_count(
        valuation
    )

    roi = None

    if total_cost > 0:

        roi = (
            profit
            /
            total_cost
            *
            100
        )

    # ========================================================
    # PROFIT — MAX 40
    # ========================================================

    score = 0
    reasons = []

    if profit >= 1200:

        score += 40
        reasons.append(
            "bardzo wysoki zysk"
        )

    elif profit >= 900:

        score += 37
        reasons.append(
            "bardzo dobry zysk"
        )

    elif profit >= 700:

        score += 34
        reasons.append(
            "wysoki zysk"
        )

    elif profit >= 550:

        score += 30
        reasons.append(
            "dobry zysk"
        )

    elif profit >= 450:

        score += 26
        reasons.append(
            "sensowny zysk"
        )

    elif profit >= 400:

        score += 22
        reasons.append(
            "minimalna dobra marża"
        )

    elif profit >= 300:

        score += 14

    # ========================================================
    # ROI — MAX 25
    # ========================================================

    if roi is not None:

        if roi >= 50:

            score += 25
            reasons.append(
                "świetne ROI"
            )

        elif roi >= 40:

            score += 23
            reasons.append(
                "bardzo wysokie ROI"
            )

        elif roi >= 30:

            score += 21
            reasons.append(
                "wysokie ROI"
            )

        elif roi >= 25:

            score += 18

        elif roi >= 20:

            score += 15

        elif roi >= 15:

            score += 10

        elif roi >= 10:

            score += 5

    # ========================================================
    # CONFIDENCE — MAX 15
    # ========================================================

    confidence_points = {
        "VERY_HIGH": 15,
        "HIGH": 13,
        "MEDIUM": 8,
        "LOW": 3,
        "VERY_LOW": 0,
    }

    score += confidence_points.get(
        confidence,
        5,
    )

    if confidence in [
        "HIGH",
        "VERY_HIGH",
    ]:

        reasons.append(
            "wysoka pewność wyceny"
        )

    # ========================================================
    # MARKET DATA — MAX 10
    # ========================================================

    if samples >= 20:

        score += 10
        reasons.append(
            "dużo danych rynkowych"
        )

    elif samples >= 10:

        score += 8
        reasons.append(
            "dobre pokrycie rynku"
        )

    elif samples >= 5:

        score += 5

    elif samples >= 1:

        score += 2

    # ========================================================
    # EXTRA
    # ========================================================

    if hot:

        score += 5

    if strong_bundle:

        score += 4

        reasons.append(
            "mocny bundle"
        )

    trigger = str(
        details.get(
            "_trigger"
        )
        or ""
    ).upper()

    if trigger in [
        "PRICE_DROP",
        "BUNDLE_PRICE_DROP",
    ]:

        score += 2

        reasons.append(
            "cena została obniżona"
        )

    if str(
        mode or ""
    ).upper() == "LOCAL":

        score += 2

    # ========================================================
    # RISK PENALTIES
    # ========================================================

    issue_penalty = min(
        len(issues) * 2,
        10,
    )

    missing_penalty = min(
        len(missing),
        5,
    )

    score -= (
        issue_penalty
        +
        missing_penalty
    )

    if ai_condition in [
        "risky",
        "poor",
    ]:

        score -= 8

    elif ai_condition == "bad":

        score -= 15

    score = max(
        0,
        min(
            100,
            int(
                round(score)
            ),
        ),
    )

    return {
        "score":
            score,

        "roi":
            roi,

        "reasons":
            reasons[:4],

        "issues":
            issues,

        "missing":
            missing,

        "purchase_price":
            purchase_price,

        "quick_sale":
            quick_sale,

        "total_cost":
            total_cost,

        "profit":
            profit,

        "bundle":
            bundle,
    }


def score_label(score):

    if score >= 90:

        return (
            "🚨 TOP OKAZJA — REAGUJ SZYBKO"
        )

    if score >= 80:

        return (
            "🔥 BARDZO MOCNA OKAZJA"
        )

    if score >= 70:

        return (
            "✅ DOBRA OKAZJA"
        )

    if score >= 60:

        return (
            "🟡 WARTA SPRAWDZENIA"
        )

    return (
        "⚪ OKAZJA DO WERYFIKACJI"
    )


# ============================================================
# NEGOTIATION
# ============================================================

def negotiation_values(
    details,
    valuation,
):

    purchase = to_float(
        details.get(
            "price"
        )
    )

    quick_sale = to_float(
        valuation.get(
            "quick_sale"
        )
    )

    total_cost = to_float(
        valuation.get(
            "total_cost"
        )
    )

    bundle = bool(
        valuation.get(
            "bundle_detected"
        )
    )

    if (
        purchase is None
        or
        quick_sale is None
    ):

        return {
            "max_buy":
                None,

            "opening":
                None,

            "target_profit":
                None,
        }

    extra_cost = 0

    if total_cost is not None:

        extra_cost = max(
            0,
            total_cost
            -
            purchase
        )

    if bundle:

        target_profit = max(
            650,
            quick_sale
            * 0.10,
        )

    elif quick_sale >= 3500:

        target_profit = 600

    elif quick_sale >= 2200:

        target_profit = 500

    else:

        target_profit = 400

    max_buy = (
        quick_sale
        -
        extra_cost
        -
        target_profit
    )

    max_buy = floor_50(
        max_buy
    )

    if max_buy is None:

        return {
            "max_buy":
                None,

            "opening":
                None,

            "target_profit":
                floor_50(
                    target_profit
                ),
        }

    opening = min(
        purchase * 0.90,
        max_buy * 0.90,
    )

    opening = floor_50(
        opening
    )

    return {
        "max_buy":
            max_buy,

        "opening":
            opening,

        "target_profit":
            floor_50(
                target_profit
            ),
    }


# ============================================================
# TELEGRAM
# ============================================================

def send_message(message):

    if not BOT_TOKEN:

        print(
            "[TELEGRAM] Brak TELEGRAM_BOT_TOKEN"
        )

        return False

    if not CHAT_ID:

        print(
            "[TELEGRAM] Brak TELEGRAM_CHAT_ID"
        )

        return False

    # Telegram ma limit długości wiadomości.
    if len(message) > 4000:

        message = (
            message[:3950]
            +
            "\n\n..."
        )

    url = (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/sendMessage"
    )

    payload = {
        "chat_id":
            CHAT_ID,

        "text":
            message,

        "parse_mode":
            "HTML",

        "disable_web_page_preview":
            True,
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=15,
        )

    except Exception as e:

        print(
            "[TELEGRAM] Błąd połączenia:",
            e
        )

        return False

    if not response.ok:

        print(
            "[TELEGRAM] Błąd API:",
            response.status_code,
            response.text[:500],
        )

        return False

    print(
        "[TELEGRAM] Alert wysłany"
    )

    return True


# ============================================================
# FLIP ALERT V4
# ============================================================

def send_flip_alert(
    details,
    valuation,
    mode,
    offer_url,
    return_status=False,
):

    details = (
        details
        or {}
    )

    valuation = (
        valuation
        or {}
    )

    result = calculate_deal_score(
        details,
        valuation,
        mode,
    )

    negotiation = negotiation_values(
        details,
        valuation,
    )

    action = calculate_action(
        details=details,
        valuation=valuation,
        score=result["score"],
    )

    # ========================================================
    # WATCHLIST
    # ========================================================

    if action.get("action") in [
        "NEGOTIATE",
        "WATCH",
    ]:

        upsert_watch(
            details=details,
            offer_url=offer_url,
            action=action,
            score=result["score"],
        )

    elif action.get("action") in [
        "BUY_NOW",
        "BUY",
    ]:

        promoted = promote_if_watched(
            details=details,
            offer_url=offer_url,
            action=action,
            score=result["score"],
        )

        if promoted:

            print(
                "[WATCHLIST] "
                "Oferta osiągnęła cenę zakupu."
            )

    # WATCH/SKIP zostaja w historii, bez Telegrama.
    if action.get("action") in ("WATCH", "SKIP"):
        save_snapshot(
            details=details,
            valuation=valuation,
            action=action,
            offer_url=offer_url,
            score=result["score"],
            mode=mode,
        )
        if action.get("action") == "WATCH":
            try:
                from watch_review_alert import send_watch_review
                delivered = send_watch_review(
                    details, valuation, action, offer_url, send_message
                )
                print("[WATCH-REVIEW]", "SENT" if delivered else "SKIPPED")
            except Exception as error:
                print("[WATCH-REVIEW] ERROR:", type(error).__name__)
        print("[TELEGRAM] SUPPRESSED:", action.get("action"))
        return "SUPPRESSED" if return_status else False

    score = result[
        "score"
    ]

    roi = result[
        "roi"
    ]

    profit = result[
        "profit"
    ]

    bundle = result[
        "bundle"
    ]

    trigger = details.get(
        "_trigger"
    )

    # ========================================================
    # HEADER
    # ========================================================

    message = (
        f"<b>{action['label']}</b>\n"
        f"<b>{score_label(score)}</b>\n"
        f"<b>DEAL SCORE: {score}/100</b>\n\n"
        f"{esc(action['reason'])}\n\n"
    )

    message += (
        f"<b>{esc(details.get('title'))}</b>\n\n"
    )

    # ========================================================
    # MONEY FIRST
    # ========================================================

    message += (
        "<b>💰 FINANSE</b>\n"

        f"Cena OLX: "
        f"<b>{money(details.get('price'))}</b>\n"

        f"Szybka sprzedaż: "
        f"<b>{money(valuation.get('quick_sale'))}</b>\n"

        f"Koszt całkowity: "
        f"{money(valuation.get('total_cost'))}\n"

        f"Zysk: "
        f"<b>{money(profit)}</b>\n"

        f"ROI: "
        f"<b>{percent(roi)}</b>\n"
    )

    # ========================================================
    # NEGOTIATION
    # ========================================================

    max_buy = negotiation.get(
        "max_buy"
    )

    opening = negotiation.get(
        "opening"
    )

    if (
        max_buy is not None
        or
        opening is not None
    ):

        message += (
            "\n<b>💬 NEGOCJACJA</b>\n"
        )

        if opening is not None:

            message += (
                f"Zacznij od: "
                f"<b>{money(opening)}</b>\n"
            )

        if max_buy is not None:

            message += (
                f"Maksymalnie daj: "
                f"<b>{money(max_buy)}</b>\n"
            )

    # ========================================================
    # SPECS
    # ========================================================

    message += (
        "\n<b>🖥 SPECYFIKACJA</b>\n"

        f"CPU: "
        f"<b>{esc(details.get('cpu'))}</b>\n"

        f"GPU: "
        f"<b>{esc(details.get('gpu'))}</b>\n"

        f"RAM: "
        f"<b>{ram_text(details.get('ram'))}</b>\n"

        f"Dyski: "
        f"{disk_text(details.get('disks'))}\n"
    )

    # ========================================================
    # BUNDLE
    # ========================================================

    if bundle:

        message += (
            "\n<b>🎮 ZESTAW / DODATKI</b>\n"
        )

        pc_value = (
            valuation.get(
                "bundle_pc_quick_sale"
            )
        )

        accessory_value = (
            valuation.get(
                "bundle_accessory_value"
            )
        )

        if accessory_value is None:

            accessory_value = (
                valuation.get(
                    "bundle_accessory_applied"
                )
            )

        if accessory_value is None:

            accessory_value = (
                valuation.get(
                    "bundle_accessory_value_applied"
                )
            )

        message += (
            f"Sam PC: "
            f"{money(pc_value)}\n"

            f"Dodatki: "
            f"<b>{money(accessory_value)}</b>\n"
        )

        items = safe_list(
            valuation.get(
                "bundle_items"
            )
        )

        for item in items[:8]:

            if isinstance(
                item,
                dict
            ):

                label = (
                    item.get(
                        "label"
                    )
                    or
                    item.get(
                        "name"
                    )
                    or
                    "Dodatek"
                )

                value = (
                    item.get(
                        "quick_value"
                    )
                )

                if value is None:

                    value = (
                        item.get(
                            "value"
                        )
                    )

                message += (
                    f"• {esc(label)}: "
                    f"{money(value)}\n"
                )

            else:

                message += (
                    f"• {esc(item)}\n"
                )

    # ========================================================
    # WHY SCORE
    # ========================================================

    reasons = result.get(
        "reasons"
    ) or []

    if reasons:

        message += (
            "\n<b>🎯 DLACZEGO WARTO</b>\n"
        )

        for reason in reasons:

            message += (
                f"✅ {esc(reason)}\n"
            )

    # ========================================================
    # MARKET
    # ========================================================

    message += (
        "\n<b>📊 RYNEK</b>\n"

        f"Źródło: "
        f"{esc(translate_source(valuation.get('valuation_source')))}\n"

        f"Pewność: "
        f"<b>{esc(translate_confidence(valuation.get('confidence')))}</b>\n"
    )

    exact_samples = valuation.get(
        "exact_samples"
    )

    similar_samples = valuation.get(
        "similar_samples"
    )

    neighbor_samples = valuation.get(
        "neighbor_samples"
    )

    market_samples = valuation.get(
        "market_samples"
    )

    if exact_samples is not None:

        message += (
            f"Identyczne: "
            f"{esc(exact_samples)}\n"
        )

    if similar_samples is not None:

        message += (
            f"Podobne: "
            f"{esc(similar_samples)}\n"
        )

    if neighbor_samples is not None:

        message += (
            f"Podobne GPU: "
            f"{esc(neighbor_samples)}\n"
        )

    if market_samples is not None:

        message += (
            f"Próbki rynku: "
            f"{esc(market_samples)}\n"
        )

    # ========================================================
    # RISK
    # ========================================================

    issues = result.get(
        "issues"
    ) or []

    missing = result.get(
        "missing"
    ) or []

    ai_condition = valuation.get(
        "ai_condition"
    )

    ai_summary = valuation.get(
        "ai_summary"
    )

    message += (
        "\n<b>⚠️ RYZYKO / SPRAWDŹ</b>\n"
    )

    if ai_condition:

        message += (
            f"Stan: "
            f"{esc(translate_condition(ai_condition))}\n"
        )

    if issues:

        for issue in issues[:5]:

            message += (
                f"• {esc(issue)}\n"
            )

    if missing:

        for item in missing[:5]:

            message += (
                f"• brak: {esc(item)}\n"
            )

    if (
        not issues
        and
        not missing
    ):

        message += (
            "Brak istotnych problemów wykrytych automatycznie.\n"
        )

    if ai_summary:

        message += (
            f"\n<i>{esc(ai_summary)}</i>\n"
        )

    # ========================================================
    # META
    # ========================================================

    message += (
        "\n<b>📍 OFERTA</b>\n"

        f"{esc(translate_trigger(trigger))}\n"

        f"{esc(translate_mode(mode))}\n"
    )

    if valuation.get(
        "bundle_pickup_override"
    ):

        message += (
            "Odbiór osobisty — brak Przesyłki OLX\n"
        )

    elif details.get(
        "shipping"
    ):

        message += (
            "Przesyłka OLX dostępna\n"
        )

    if details.get(
        "_spec_ai_used"
    ):

        message += (
            "Specyfikacja częściowo uzupełniona przez AI\n"
        )

    # ========================================================
    # LINK
    # ========================================================

    message += (
        "\n"
        f'<a href="{esc(offer_url)}">'
        "<b>👉 OTWÓRZ OGŁOSZENIE OLX</b>"
        "</a>"
    )

    # ========================================================
    # DUPLICATE PROTECTION
    # ========================================================

    if already_sent(
        details,
        offer_url,
    ):

        print(
            "[TELEGRAM] Duplikat pominięty: "
            f"{details.get('title')} | "
            f"{details.get('price')}"
        )

        return "SUPPRESSED" if return_status else False

    sent = send_message(
        message
    )

    if sent:

        record_alert(
            details=details,
            valuation=valuation,
            offer_url=offer_url,
            score=score,
            mode=mode,
        )

        save_snapshot(
            details=details,
            valuation=valuation,
            action=action,
            offer_url=offer_url,
            score=score,
            mode=mode,
        )

        # ====================================================
        # TOP DEAL — PILNY ALERT
        # ====================================================

        if action.get("action") == "BUY_NOW":

            urgent_message = (
                "🚨🚨 <b>TOP DEAL — KUP TERAZ</b> 🚨🚨\n\n"
                f"<b>{esc(details.get('title'))}</b>\n\n"
                f"💰 Cena: <b>{money(details.get('price'))}</b>\n"
                f"⚡ Szybka sprzedaż: <b>{money(valuation.get('quick_sale'))}</b>\n"
                f"💵 Zysk: <b>{money(valuation.get('profit'))}</b>\n"
                f"📈 ROI: <b>{percent(action.get('roi'))}</b>\n"
                f"🎯 Score: <b>{score}/100</b>\n\n"
                f"💬 Zacznij od: <b>{money(action.get('opening'))}</b>\n"
                f"🛑 Maksymalnie daj: <b>{money(action.get('max_buy'))}</b>\n\n"
                f'<a href="{esc(offer_url)}">'
                "<b>👉 OTWÓRZ OLX TERAZ</b>"
                "</a>"
            )

            send_message(
                urgent_message
            )

    if return_status:
        return "SENT" if sent else "ERROR"
    return bool(sent)
