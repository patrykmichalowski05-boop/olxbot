import math


MIN_PROFIT = 400
TARGET_PROFIT = 550


def _price_99(value):
    """
    Zaokrąglenie ceny wystawienia
    do atrakcyjnej końcówki 99.
    """
    value = float(value)

    hundreds = math.ceil(
        value / 100
    ) * 100

    return max(
        99,
        hundreds - 1,
    )


def _round_50(value):
    return round(
        float(value) / 50
    ) * 50


def calculate_sale_prices(
    total_investment,
    quick_sale=None,
):
    total = float(
        total_investment or 0
    )

    market_quick = (
        float(quick_sale)
        if quick_sale
        else None
    )


    # Absolutne minimum wynikające
    # z naszego celu zysku.
    profit_minimum = (
        total
        + MIN_PROFIT
    )

    target_by_profit = (
        total
        + TARGET_PROFIT
    )


    # Jeśli znamy quick sale,
    # cena wystawienia powinna mieć
    # miejsce na negocjacje.
    if market_quick:

        target_raw = max(
            target_by_profit,
            market_quick * 1.08,
        )

        minimum_raw = max(
            profit_minimum,
            market_quick,
        )

    else:

        target_raw = (
            target_by_profit
        )

        minimum_raw = (
            profit_minimum
        )


    target_price = (
        _price_99(
            target_raw
        )
    )

    minimum_price = (
        _round_50(
            minimum_raw
        )
    )


    # Minimum nigdy nie może być
    # wyższe od ceny wystawienia.
    minimum_price = min(
        minimum_price,
        target_price,
    )


    target_profit = (
        target_price
        - total
    )

    minimum_profit = (
        minimum_price
        - total
    )


    if (
        market_quick
        and market_quick
        < profit_minimum
    ):

        status = (
            "LOW_MARGIN"
        )

        warning = (
            "Rynek może nie pozwolić osiągnąć "
            f"minimum {MIN_PROFIT} zł zysku."
        )

    elif minimum_profit >= MIN_PROFIT:

        status = (
            "GOOD"
        )

        warning = None

    else:

        status = (
            "WARNING"
        )

        warning = (
            "Marża jest niższa od założonego minimum."
        )


    return {
        "total_investment":
            total,

        "quick_sale":
            market_quick,

        "target_price":
            target_price,

        "minimum_price":
            minimum_price,

        "target_profit":
            target_profit,

        "minimum_profit":
            minimum_profit,

        "required_profit":
            MIN_PROFIT,

        "status":
            status,

        "warning":
            warning,
    }
