from __future__ import annotations

from datetime import datetime, timedelta, timezone

from universal_v2.valuation import calculate

from .matching import comparable_key, matches, risks
from .models import Costs, Offer, Search, timestamp


def quote(buy: int, resale: int, costs: Costs, min_profit: int, min_roi: int) -> dict:
    value = calculate(buy, resale, costs.amounts(buy, resale), min_profit)
    # Both ROI and absolute profit constrain the ceiling. Percentage costs
    # depend on the purchase price, so solve using integer binary search.
    lo, hi, ceiling = 0, resale, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = calculate(mid, resale, costs.amounts(mid, resale), min_profit)
        if candidate["profit_minor"] >= min_profit and (
            mid + candidate["cost_minor"] == 0 or candidate["roi_bps"] >= min_roi
        ):
            ceiling, lo = mid, mid + 1
        else:
            hi = mid - 1
    value.update(
        max_buy_minor=max(0, ceiling),
        affordable=ceiling >= buy,
        costs=costs.amounts(buy, resale),
    )
    return value


def estimate(
    offer: Offer, search: Search, peers: list[Offer], now: datetime | None = None
) -> dict:
    now = now or datetime.now(timezone.utc)
    key = comparable_key(offer, search)
    if not key:
        return {
            "status": "NO_RELIABLE_VALUATION",
            "reason": "Niepełne dane modelu lub wariantu",
        }
    cutoff = now - timedelta(days=search.reference_days)
    independent = {}
    for peer in peers:
        if (
            peer.key == offer.key
            or peer.currency != offer.currency
            or peer.price_minor in (None, 0)
        ):
            continue
        if (
            peer.status == "REMOVED"
            or timestamp(peer.observed_at) < cutoff
            or timestamp(peer.observed_at) > now + timedelta(minutes=5)
        ):
            continue
        if comparable_key(peer, search) != key:
            continue
        # One seller contributes one reference when an identifier is available.
        identity = peer.seller_key or peer.key
        previous = independent.get(identity)
        if previous is None or (
            peer.status == "SOLD_VERIFIED" and previous.status != "SOLD_VERIFIED"
        ):
            independent[identity] = peer
        elif previous.status == peer.status and peer.price_minor < previous.price_minor:
            independent[identity] = peer
    sold = [row for row in independent.values() if row.status == "SOLD_VERIFIED"]
    selected = (
        sold
        if len(sold) >= search.min_comparables
        else [row for row in independent.values() if row.status == "ACTIVE"]
    )
    prices = sorted(row.price_minor for row in selected)
    if len(prices) < search.min_comparables:
        return {
            "status": "NO_RELIABLE_VALUATION",
            "reason": "Za mało porównywalnych ofert",
            "sample_count": len(prices),
        }
    median = prices[(len(prices) - 1) // 2]
    # Remove gross outliers, then measure dispersion on the remaining prices.
    prices = [value for value in prices if median // 2 <= value <= median * 2]
    if len(prices) < search.min_comparables:
        return {
            "status": "NO_RELIABLE_VALUATION",
            "reason": "Za mało ofert po odrzuceniu odstających cen",
        }
    low = prices[(len(prices) - 1) // 4]
    high = prices[3 * (len(prices) - 1) // 4]
    median = prices[(len(prices) - 1) // 2]
    if (high - low) * 10000 > median * search.max_spread_bps:
        return {
            "status": "NO_RELIABLE_VALUATION",
            "reason": "Zbyt duży rozrzut cen porównawczych",
        }
    kind = "SOLD_VERIFIED" if len(sold) >= search.min_comparables else "ASKING"
    haircut = 0 if kind == "SOLD_VERIFIED" else search.asking_haircut_bps
    resale = low * (10000 - haircut) // 10000
    return {
        "status": "OK",
        "kind": kind,
        "sample_count": len(prices),
        "low_minor": low,
        "median_minor": median,
        "high_minor": high,
        "resale_minor": resale,
        "haircut_bps": haircut,
        "confidence": "HIGH" if kind == "SOLD_VERIFIED" else "LOW",
    }


def evaluate(
    offer: Offer, search: Search, peers: list[Offer], now: datetime | None = None
) -> dict:
    now = now or datetime.now(timezone.utc)
    warning = risks(offer)
    base = {
        "decision": "SKIP",
        "qualifies": False,
        "warnings": warning,
        "category": search.category,
        "valuation": None,
        "market": None,
        "insight": "Oferta nie spełnia wybranych kryteriów.",
    }
    if (
        not matches(offer, search)
        or offer.status != "ACTIVE"
        or warning
        or offer.price_minor in (None, 0)
    ):
        return base
    if timestamp(offer.observed_at) > now + timedelta(minutes=5) or timestamp(
        offer.observed_at
    ) < now - timedelta(days=search.reference_days):
        return {**base, "insight": "Oferta nie ma aktualnej daty obserwacji."}
    if (
        search.max_price_minor is not None
        and offer.price_minor > search.max_price_minor
    ):
        return base
    market = estimate(offer, search, peers, now)
    base["market"] = market
    if market["status"] != "OK":
        base.update(decision="NO_RELIABLE_VALUATION", insight=market["reason"])
        if search.purpose == "cheap":
            base.update(
                decision="WATCH",
                qualifies=True,
                insight="Cena mieści się w ustawionym limicie. Brak wiarygodnej prognozy odsprzedaży.",
            )
        return base
    value = quote(
        offer.price_minor,
        market["resale_minor"],
        search.costs,
        search.min_profit_minor,
        search.min_roi_bps,
    )
    base["valuation"] = value
    discount = (
        (market["median_minor"] - offer.price_minor) * 10000 // market["median_minor"]
    )
    qualifies = value["affordable"] and discount >= search.min_discount_bps
    if search.purpose == "cheap":
        qualifies = True
    if market["kind"] == "ASKING":
        warning.append(
            "Prognoza oparta na cenach ofertowych, nie na potwierdzonych sprzedażach"
        )
        qualifies = qualifies and (
            search.allow_asking_alerts or search.purpose == "cheap"
        )
    if offer.condition == "UNKNOWN":
        warning.append("Stan przedmiotu wymaga weryfikacji")
    if search.category == "FASHION":
        warning.append("Autentyczność wymaga weryfikacji")
    base.update(
        decision=(
            "BUY_CANDIDATE"
            if qualifies and market["kind"] == "SOLD_VERIFIED" and not warning
            else "WATCH"
        ),
        qualifies=qualifies,
        discount_bps=discount,
        insight=f"Porównano {market['sample_count']} ofert tego wariantu. Wynik uwzględnia koszty i rezerwę; jest prognozą przed podatkiem.",
    )
    return base
