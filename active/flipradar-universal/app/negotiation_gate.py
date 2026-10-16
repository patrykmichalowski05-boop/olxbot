import math

from telegram_notifier import negotiation_values


MAX_DISCOUNT_PLN = 200
MAX_DISCOUNT_PERCENT = 0.10


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def negotiation_candidate(details, valuation):
    """
    True oznacza tylko potencjalna oplacalnosc
    po realistycznej negocjacji.

    Nie oznacza pewnego rabatu ani decyzji KUP TERAZ.
    """

    details = details or {}
    valuation = valuation or {}

    price = number(details.get("price"))
    quick_sale = number(valuation.get("quick_sale"))
    total_cost = number(valuation.get("total_cost"))
    profit = number(valuation.get("profit"))

    if any(v is None for v in (
        price, quick_sale, total_cost, profit
    )):
        return False

    if price <= 0 or quick_sale <= 0:
        return False

    if total_cost < price:
        return False

    # Nie ufamy niespojnym danym wyceny.
    if abs(profit - (quick_sale - total_cost)) > 25:
        return False

    negotiation = negotiation_values(
        details,
        valuation,
    )

    max_buy = number(negotiation.get("max_buy"))
    target = number(negotiation.get("target_profit"))

    if max_buy is None or target is None:
        return False

    if valuation.get("bundle_detected"):
        target = max(target, 650)

    required_discount = max(
        0,
        price - max_buy,
        target - profit,
    )

    allowed_discount = min(
        MAX_DISCOUNT_PLN,
        price * MAX_DISCOUNT_PERCENT,
    )

    return (
        required_discount > 0
        and required_discount <= allowed_discount
    )
