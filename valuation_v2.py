from valuation import static_valuation

from market_stats import (
    get_cpu_gpu_stats
)

from similarity_engine import (
    similar_market_stats
)


# ============================================================
# PARAMETRY
# ============================================================

MIN_PROFIT = 400
HOT_PROFIT = 700


# ============================================================
# HELPERY
# ============================================================

def weighted_average(items):
    """
    items:
    [
        (value, weight),
        ...
    ]
    """

    valid = [
        (value, weight)
        for value, weight in items
        if (
            value is not None
            and
            weight > 0
        )
    ]

    if not valid:
        return None

    total_weight = sum(
        weight
        for _, weight
        in valid
    )

    if total_weight <= 0:
        return None

    return round(
        sum(
            value * weight
            for value, weight
            in valid
        )
        / total_weight
    )


def sanity_cap(
    value,
    static_value,
    exact_samples
):
    """
    Market może być drogi, bo aktywne OLX
    zawiera dużo niesprzedawalnych ofert.

    Im więcej identycznych komputerów,
    tym bardziej pozwalamy odejść od fallbacku.
    """

    if not static_value:
        return value, False, None

    if exact_samples >= 10:
        multiplier = 1.40

    elif exact_samples >= 5:
        multiplier = 1.35

    elif exact_samples >= 3:
        multiplier = 1.25

    elif exact_samples >= 1:
        multiplier = 1.20

    else:
        multiplier = 1.15

    maximum = round(
        static_value
        * multiplier
    )

    if (
        value is not None
        and
        value > maximum
    ):

        return (
            maximum,
            True,
            maximum
        )

    return (
        value,
        False,
        maximum
    )


# ============================================================
# WYBÓR WYCENY
# ============================================================

def choose_market_value(
    static_quick,
    exact,
    similar
):

    exact_samples = exact.get(
        "samples",
        0
    )

    exact_quick = exact.get(
        "quick_sale"
    )

    similar_samples = similar.get(
        "samples",
        0
    )

    similar_quick = similar.get(
        "quick_sale"
    )

    similarity = similar.get(
        "avg_similarity"
    ) or 0

    # ========================================================
    # 10+ IDENTYCZNYCH
    # ========================================================

    if (
        exact_samples >= 10
        and
        exact_quick
    ):

        value = weighted_average([
            (
                exact_quick,
                0.80
            ),
            (
                similar_quick,
                0.20
            )
        ])

        source = (
            "EXACT_MARKET"
        )

        confidence = (
            "BARDZO WYSOKI"
        )

    # ========================================================
    # 5-9 IDENTYCZNYCH
    # ========================================================

    elif (
        exact_samples >= 5
        and
        exact_quick
    ):

        value = weighted_average([
            (
                exact_quick,
                0.70
            ),
            (
                similar_quick,
                0.20
            ),
            (
                static_quick,
                0.10
            )
        ])

        source = (
            "EXACT+SIMILAR"
        )

        confidence = (
            "WYSOKI"
        )

    # ========================================================
    # 3-4 IDENTYCZNE
    # ========================================================

    elif (
        exact_samples >= 3
        and
        exact_quick
    ):

        value = weighted_average([
            (
                exact_quick,
                0.60
            ),
            (
                similar_quick,
                0.20
            ),
            (
                static_quick,
                0.20
            )
        ])

        source = (
            "MARKET+SIMILAR+STATIC"
        )

        confidence = (
            "ŚREDNI"
        )

    # ========================================================
    # 1-2 IDENTYCZNE
    # ========================================================

    elif (
        exact_samples >= 1
        and
        exact_quick
    ):

        if (
            similar_samples >= 5
            and
            similarity >= 88
        ):

            value = weighted_average([
                (
                    exact_quick,
                    0.25
                ),
                (
                    similar_quick,
                    0.40
                ),
                (
                    static_quick,
                    0.35
                )
            ])

            source = (
                "SIMILAR+STATIC"
            )

        else:

            value = weighted_average([
                (
                    exact_quick,
                    0.25
                ),
                (
                    static_quick,
                    0.75
                )
            ])

            source = (
                "STATIC+EXACT"
            )

        confidence = (
            "NISKI"
        )

    # ========================================================
    # BRAK IDENTYCZNYCH
    # ========================================================

    elif (
        similar_samples >= 5
        and
        similarity >= 90
        and
        similar_quick
        and
        static_quick
    ):

        # Brak identycznego zestawu.
        # Similar market nie może samodzielnie
        # ustalić ceny.

        value = weighted_average([
            (
                similar_quick,
                0.50
            ),
            (
                static_quick,
                0.50
            )
        ])

        source = (
            "SIMILAR+STATIC"
        )

        confidence = (
            "NISKI"
        )

    # ========================================================
    # SŁABE DANE RYNKOWE
    # ========================================================

    elif static_quick:

        value = (
            static_quick
        )

        source = (
            "STATIC"
        )

        confidence = (
            "FALLBACK"
        )

    else:

        return {
            "ok": False,
            "reason":
                "Brak wiarygodnej wyceny"
        }

    # ========================================================
    # SANITY CAP
    # ========================================================

    value_before_cap = (
        value
    )

    value, capped, cap = (
        sanity_cap(
            value,
            static_quick,
            exact_samples
        )
    )

    return {
        "ok": True,

        "quick_sale":
            round(value),

        "quick_sale_before_cap":
            value_before_cap,

        "sanity_cap_applied":
            capped,

        "sanity_cap":
            cap,

        "valuation_source":
            source,

        "confidence":
            confidence,

        "exact_samples":
            exact_samples,

        "exact_quick_sale":
            exact_quick,

        "similar_samples":
            similar_samples,

        "similar_quick_sale":
            similar_quick,

        "avg_similarity":
            similarity
    }


# ============================================================
# GŁÓWNA WYCENA V2
# ============================================================

def estimate_flip_v2(
    details,
    mode
):

    purchase_price = details.get(
        "price"
    )

    cpu = details.get(
        "cpu"
    )

    gpu = details.get(
        "gpu"
    )

    ram = details.get(
        "ram"
    )

    if not purchase_price:

        return {
            "ok": False,
            "reason":
                "Brak ceny zakupu"
        }

    if not cpu:

        return {
            "ok": False,
            "reason":
                "Brak CPU"
        }

    if not gpu:

        return {
            "ok": False,
            "reason":
                "Brak GPU"
        }

    # ========================================================
    # STATIC
    # ========================================================

    static = static_valuation(
        details
    )

    static_quick = None

    if static.get("ok"):

        static_quick = (
            static.get(
                "quick_sale"
            )
        )

    # ========================================================
    # IDENTYCZNE CPU + GPU
    # ========================================================

    exact = get_cpu_gpu_stats(
        cpu,
        gpu,
        max_age_hours=720
    )

    # ========================================================
    # PODOBNE PC
    # ========================================================

    similar = similar_market_stats(
        cpu,
        gpu,
        ram
    )

    # ========================================================
    # HYBRYDA
    # ========================================================

    selected = choose_market_value(
        static_quick,
        exact,
        similar
    )

    if not selected.get(
        "ok"
    ):

        return selected

    quick_sale = selected[
        "quick_sale"
    ]

    # ========================================================
    # KOSZTY
    # ========================================================

    service_reserve = 100

    shipping_cost = (
        50
        if mode == "POLSKA"
        else 0
    )

    total_cost = (
        purchase_price
        +
        service_reserve
        +
        shipping_cost
    )

    profit = (
        quick_sale
        -
        total_cost
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "ok": True,

        "purchase_price":
            purchase_price,

        "quick_sale":
            quick_sale,

        "profit":
            round(profit),

        "total_cost":
            total_cost,

        "shipping_cost":
            shipping_cost,

        "service_reserve":
            service_reserve,

        "profitable":
            profit >= MIN_PROFIT,

        "hot":
            profit >= HOT_PROFIT,

        # ----------------------------------------
        # ŹRÓDŁO
        # ----------------------------------------

        "valuation_source":
            selected[
                "valuation_source"
            ],

        "confidence":
            selected[
                "confidence"
            ],

        # ----------------------------------------
        # STATIC
        # ----------------------------------------

        "static_quick_sale":
            static_quick,

        # ----------------------------------------
        # EXACT
        # ----------------------------------------

        "market_samples":
            selected[
                "exact_samples"
            ],

        "exact_samples":
            selected[
                "exact_samples"
            ],

        "exact_quick_sale":
            selected[
                "exact_quick_sale"
            ],

        "market_min":
            exact.get(
                "min"
            ),

        "market_p25":
            exact.get(
                "p25"
            ),

        "market_median":
            exact.get(
                "median"
            ),

        "market_p75":
            exact.get(
                "p75"
            ),

        # ----------------------------------------
        # SIMILAR
        # ----------------------------------------

        "similar_samples":
            selected[
                "similar_samples"
            ],

        "similar_quick_sale":
            selected[
                "similar_quick_sale"
            ],

        "similarity":
            selected[
                "avg_similarity"
            ],

        "similar_median":
            similar.get(
                "median"
            ),

        "similar_p25":
            similar.get(
                "p25"
            ),

        # ----------------------------------------
        # BEZPIECZNIK
        # ----------------------------------------

        "quick_sale_before_cap":
            selected[
                "quick_sale_before_cap"
            ],

        "sanity_cap_applied":
            selected[
                "sanity_cap_applied"
            ],

        "sanity_cap":
            selected[
                "sanity_cap"
            ],
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    tests = [
        {
            "cpu":
                "Ryzen 5 3600",

            "gpu":
                "RTX 3060",

            "ram":
                16,

            "disks":
                ["NVME 1 TB"],

            "price":
                1400
        },

        {
            "cpu":
                "i5-12400F",

            "gpu":
                "RTX 3060",

            "ram":
                16,

            "disks":
                ["NVME 1 TB"],

            "price":
                1700
        },

        {
            "cpu":
                "Ryzen 5 5600",

            "gpu":
                "RTX 3060",

            "ram":
                16,

            "disks":
                ["NVME 1 TB"],

            "price":
                1500
        }
    ]

    for details in tests:

        print()
        print("=" * 75)

        print(
            details["cpu"],
            "+",
            details["gpu"]
        )

        result = estimate_flip_v2(
            details,
            "POLSKA"
        )

        for key, value in (
            result.items()
        ):

            print(
                f"{key:25}: "
                f"{value}"
            )
