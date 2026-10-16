import math


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


def floor_50(value):

    value = to_float(
        value
    )

    if value is None:
        return None

    return int(
        math.floor(
            value / 50
        )
        * 50
    )


def calculate_action(
    details,
    valuation,
    score=None,
):

    from negotiation_gate import (
        negotiation_candidate,
        MAX_DISCOUNT_PLN,
        MAX_DISCOUNT_PERCENT,
    )

    details = (
        details
        or {}
    )

    valuation = (
        valuation
        or {}
    )

    price = to_float(
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

    profit = to_float(
        valuation.get(
            "profit"
        ),
        0,
    )

    score = to_float(
        score,
        0,
    )

    confidence = str(
        valuation.get(
            "confidence"
        )
        or ""
    ).upper()

    # Ujednolicenie poziomow pewnosci PL / EN.
    confidence_aliases = {
        "ŚREDNI": "MEDIUM",
        "SREDNI": "MEDIUM",
        "WYSOKI": "HIGH",
        "BARDZO WYSOKI": "VERY_HIGH",
        "BARDZO_WYSOKI": "VERY_HIGH",
        "NISKI": "LOW",
        "BARDZO NISKI": "VERY_LOW",
        "BRAK": "NONE",
    }

    confidence = confidence_aliases.get(
        confidence,
        confidence
    )

    ai_condition = str(
        valuation.get(
            "ai_condition"
        )
        or ""
    ).lower()

    issues = (
        valuation.get(
            "ai_issues"
        )
        or []
    )

    bundle = bool(
        valuation.get(
            "bundle_detected"
        )
    )

    # ========================================================
    # ROI
    # ========================================================

    roi = None

    if (
        total_cost is not None
        and
        total_cost > 0
    ):

        roi = (
            profit
            /
            total_cost
            *
            100
        )

    # ========================================================
    # EXTRA COST
    # ========================================================

    extra_cost = 0

    if (
        total_cost is not None
        and
        price is not None
    ):

        extra_cost = max(
            0,
            total_cost
            -
            price
        )

    # ========================================================
    # TARGET PROFIT
    # ========================================================

    if bundle:

        target_profit = max(
            650,
            quick_sale * 0.10 if quick_sale is not None else 650,
        )

    elif (
        quick_sale is not None
        and
        quick_sale >= 3500
    ):

        target_profit = 600

    elif (
        quick_sale is not None
        and
        quick_sale >= 2200
    ):

        target_profit = 500

    else:

        target_profit = 400

    # ========================================================
    # MAX BUY
    # ========================================================

    max_buy = None

    if quick_sale is not None:

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

    # ========================================================
    # OPENING OFFER
    # ========================================================

    opening = None

    if (
        price is not None
        and
        max_buy is not None
    ):

        opening = min(
            price * 0.90,
            max_buy * 0.90,
        )

        opening = floor_50(
            opening
        )

    # ========================================================
    # HARD RISK
    # ========================================================

    hard_risk = (
        ai_condition
        in [
            "bad",
            "poor",
            "risky",
        ]
    )

    many_issues = (
        len(
            issues
        )
        >= 4
    )

    # ========================================================
    # DECISION
    # ========================================================

    action = "WATCH"
    label = "👀 OBSERWUJ"
    reason = (
        "Oferta wymaga dodatkowej weryfikacji."
    )

    # --------------------------------------------------------
    # SKIP
    # --------------------------------------------------------

    if hard_risk:

        action = "SKIP"

        label = (
            "⛔ ODPUSZCZ"
        )

        reason = (
            "AI wykryło podwyższone ryzyko "
            "stanu sprzętu."
        )

    # HOT WATCH ALERT:
    # Bardzo tanie, potencjalnie zyskowne zestawy
    # wymagaja pilnej weryfikacji, nie ciszy Telegrama.
    # Jawnie wysokie ryzyko jest obslugiwane wyzej.
    elif (
        profit >= 750
        and valuation.get("hot") is True
        and roi is not None
        and roi >= 50
        and price is not None
        and max_buy is not None
        and price <= max_buy
        and details.get("cpu")
        and details.get("gpu")
        and isinstance(details.get("ram"), (int, float))
        and details["ram"] >= 16
        and ai_condition not in ("bad", "poor", "risky")
    ):
        action = "REVIEW"
        label = "PILNA WERYFIKACJA - DUZA MARZA"
        reason = (
            "Potencjalnie bardzo wysoki zysk. "
            "Wycena lub stan komputera wymaga potwierdzenia. "
            "Sprawdz kompletnosc zestawu, sprawnosc, "
            "podzespoly i sprzedawce przed zakupem."
        )

    elif many_issues:

        action = "WATCH"

        label = (
            "👀 OBSERWUJ"
        )

        reason = (
            "Za dużo niewiadomych w ogłoszeniu."
        )

    # --------------------------------------------------------
    # BUY NOW
    # --------------------------------------------------------

    elif (
        score >= 85
        and
        profit >= 600
        and
        (
            roi is None
            or
            roi >= 25
        )
        and
        confidence
        in [
            "HIGH",
            "VERY_HIGH",
        ]
        and
        (
            max_buy is None
            or
            price is None
            or
            price <= max_buy
        )
    ):

        action = "BUY_NOW"

        label = (
            "🚨 KUP TERAZ"
        )

        reason = (
            "Cena już spełnia wymagania "
            "dotyczące zysku i ryzyka."
        )

    # --------------------------------------------------------
    # STRONG BUY
    # --------------------------------------------------------

    elif (
        score >= 75
        and
        profit >= 500
        and
        confidence
        in [
            "MEDIUM",
            "HIGH",
            "VERY_HIGH",
        ]
        and
        (
            max_buy is None
            or
            price is None
            or
            price <= max_buy
        )
    ):

        action = "BUY"

        label = (
            "🔥 BARDZO DOBRA OFERTA"
        )

        reason = (
            "Aktualna cena jest już "
            "opłacalna."
        )

    # --------------------------------------------------------
    # NEGOTIATE
    # --------------------------------------------------------

    elif (
        max_buy is not None
        and
        price is not None
        and
        price > max_buy
        and
        score >= 55
        and
        negotiation_candidate(details, valuation)
        and
        (
            price - max_buy
            <= min(
                MAX_DISCOUNT_PLN,
                price * MAX_DISCOUNT_PERCENT,
            )
        )
    ):

        action = "NEGOTIATE"

        label = (
            "💬 NEGOCJUJ"
        )

        difference = (
            price
            -
            max_buy
        )

        reason = (
            "Oferta będzie atrakcyjna "
            f"po zejściu o około "
            f"{int(round(difference))} zł."
        )

    # --------------------------------------------------------

    # ========================================================
    # REVIEW — dobra marza, potrzebna reczna weryfikacja
    # ========================================================

    elif (
        profit >= 600
        and score >= 65
        and confidence in ("MEDIUM", "HIGH", "VERY_HIGH")
        and roi is not None
        and roi >= 25
        and price is not None
        and max_buy is not None
        and price <= max_buy
    ):

        action = "REVIEW"
        label = "🔎 OKAZJA DO SPRAWDZENIA"
        reason = (
            "Wysoki potencjalny zysk, ale punktacja "
            "nie wystarcza do rekomendacji BUY. "
            "Zweryfikuj stan, podzespoly i sprzedawce."
        )

    # WATCH
    # --------------------------------------------------------

    elif (
        profit >= 300
        or
        score >= 60
    ):

        action = "WATCH"

        label = (
            "👀 OBSERWUJ"
        )

        reason = (
            "Jest potencjał, ale obecnie "
            "brakuje przewagi do szybkiego zakupu."
        )

    # --------------------------------------------------------
    # SKIP LOW VALUE
    # --------------------------------------------------------

    else:

        action = "SKIP"

        label = (
            "⛔ ODPUSZCZ"
        )

        reason = (
            "Za mały potencjalny zysk "
            "lub za niska jakość okazji."
        )

    return {
        "action":
            action,

        "label":
            label,

        "reason":
            reason,

        "max_buy":
            max_buy,

        "opening":
            opening,

        "target_profit":
            target_profit,

        "roi":
            roi,
    }


if __name__ == "__main__":

    test_details = {
        "price": 1650,
    }

    test_valuation = {
        "quick_sale": 2450,
        "total_cost": 1800,
        "profit": 650,
        "confidence": "HIGH",
        "ai_condition": "good",
        "ai_issues": [],
    }

    print(
        calculate_action(
            test_details,
            test_valuation,
            score=88,
        )
    )
