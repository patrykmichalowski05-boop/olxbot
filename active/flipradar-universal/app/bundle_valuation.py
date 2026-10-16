def apply_bundle_valuation(
    valuation,
    bundle,
):
    valuation = dict(
        valuation or {}
    )

    bundle = bundle or {}

    if not valuation.get("ok"):
        return valuation

    if not bundle.get("is_bundle"):
        valuation["bundle_detected"] = False
        return valuation

    raw_bonus = int(
        bundle.get(
            "accessory_quick_value",
            0
        )
        or 0
    )

    confidence = bundle.get(
        "confidence",
        "LOW"
    )

    # Konserwatywnie.
    #
    # HIGH   -> 100% naszej już ostrożnej
    #           wartości quick-sale dodatków
    #
    # MEDIUM -> 70%
    #
    # LOW    -> dodatków nie doliczamy
    #           automatycznie.

    factors = {
        "HIGH": 1.00,
        "MEDIUM": 0.70,
        "LOW": 0.00,
    }

    factor = factors.get(
        confidence,
        0.0
    )

    applied_bonus = round(
        raw_bonus * factor
    )

    pc_quick_sale = int(
        valuation.get(
            "quick_sale",
            0
        )
        or 0
    )

    total_cost = int(
        valuation.get(
            "total_cost",
            0
        )
        or 0
    )

    bundle_quick_sale = (
        pc_quick_sale
        +
        applied_bonus
    )

    profit = (
        bundle_quick_sale
        -
        total_cost
    )

    valuation[
        "bundle_detected"
    ] = True

    valuation[
        "bundle_strong"
    ] = bool(
        bundle.get(
            "strong_bundle"
        )
    )

    valuation[
        "bundle_confidence"
    ] = confidence

    valuation[
        "bundle_score"
    ] = bundle.get(
        "score"
    )

    valuation[
        "bundle_items"
    ] = bundle.get(
        "items",
        []
    )

    valuation[
        "bundle_accessory_value_raw"
    ] = raw_bonus

    valuation[
        "bundle_accessory_factor"
    ] = factor

    valuation[
        "bundle_accessory_value"
    ] = applied_bonus

    valuation[
        "bundle_pc_quick_sale"
    ] = pc_quick_sale

    valuation[
        "quick_sale"
    ] = bundle_quick_sale

    valuation[
        "profit"
    ] = profit

    valuation[
        "profitable"
    ] = (
        profit >= 400
    )

    valuation[
        "hot"
    ] = (
        profit >= 700
    )

    return valuation


if __name__ == "__main__":

    valuation = {
        "ok": True,
        "quick_sale": 6000,
        "total_cost": 5150,
        "profit": 850,
    }

    bundle = {
        "is_bundle": True,
        "strong_bundle": True,
        "confidence": "HIGH",
        "score": 10,

        "accessory_quick_value":
            1950,

        "items": [
            {
                "type": "monitor",
                "quick_value": 800,
            },
            {
                "type": "wheel",
                "quick_value": 600,
            },
            {
                "type": "shifter",
                "quick_value": 300,
            },
            {
                "type": "hotas",
                "quick_value": 250,
            },
        ],
    }

    result = apply_bundle_valuation(
        valuation,
        bundle,
    )

    for key, value in result.items():

        print(
            f"{key:30}: {value}"
        )
