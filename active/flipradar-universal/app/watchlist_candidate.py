import math

from watchlist import upsert_watch


MIN_WATCH_PROFIT = 150
MAX_WATCH_PROFIT = 399
MAX_PRICE_GAP = 800


def number(value, default=None):

    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def floor_50(value):

    value = number(value)

    if value is None:
        return None

    return int(
        math.floor(
            value / 50
        ) * 50
    )


def maybe_watch_candidate(
    details,
    valuation,
    offer_url,
):

    details = details or {}
    valuation = valuation or {}

    price = number(
        details.get("price")
    )

    quick_sale = number(
        valuation.get("quick_sale")
    )

    total_cost = number(
        valuation.get("total_cost")
    )

    profit = number(
        valuation.get("profit")
    )

    if (
        price is None
        or quick_sale is None
        or profit is None
    ):
        return False

    # Nie zaśmiecamy watchlisty ofertami kompletnie bez potencjału.
    if profit < MIN_WATCH_PROFIT:
        return False

    # >=400 zł i tak powinno przejść normalną ścieżką alertową.
    if profit > MAX_WATCH_PROFIT:
        return False

    confidence = str(
        valuation.get("confidence")
        or ""
    ).upper()

    if confidence in [
        "LOW",
        "VERY_LOW",
    ]:
        return False

    extra_cost = 0

    if total_cost is not None:

        extra_cost = max(
            0,
            total_cost - price,
        )

    bundle = bool(
        valuation.get("bundle_detected")
    )

    if bundle:

        target_profit = 650

    elif quick_sale >= 3500:

        target_profit = 600

    elif quick_sale >= 2200:

        target_profit = 500

    else:

        target_profit = 400

    max_buy = floor_50(
        quick_sale
        -
        extra_cost
        -
        target_profit
    )

    if max_buy is None:
        return False

    # Jeżeli cena już jest poniżej MAX BUY,
    # nie ma sensu wrzucać jej do oczekujących.
    if price <= max_buy:
        return False

    gap = (
        price
        -
        max_buy
    )

    # Nie obserwujemy PC, który musiałby spaść np. o 1500 zł.
    if gap > MAX_PRICE_GAP:
        return False

    opening = floor_50(
        min(
            price * 0.90,
            max_buy * 0.90,
        )
    )

    action = {
        "action":
            "PREALERT_WATCH",

        "max_buy":
            max_buy,

        "opening":
            opening,
    }

    upsert_watch(
        details=details,
        offer_url=offer_url,
        action=action,
        score=0,
    )

    print(
        "[WATCHLIST PREALERT] "
        f"{details.get('title')} | "
        f"cena={int(price)} | "
        f"max={max_buy} | "
        f"brakuje={int(gap)} | "
        f"profit={int(profit)}"
    )

    return True
