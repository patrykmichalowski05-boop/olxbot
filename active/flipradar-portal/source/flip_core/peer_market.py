"""Same-GPU, closely-related CPU asking-price scenarios. Never BUY."""

from __future__ import annotations

from .market_evidence import (
    canonical_id,
    hardware_key,
    percentile,
)

from .profit_engine import quote

# Stara tabela pomocniczych wartosci procesorow.
# Nie sa to ceny potwierdzonych sprzedazy.
from similarity_engine import CPU_REFERENCE


RESERVE_MINOR = 15000
MIN_PEERS = 5


def review_offer(
    evidence,
    category,
    price_minor,
    url="",
    status="UNKNOWN",
):
    result = {
        "decision": "REVIEW",
        "automatic_buy_allowed": False,
        "confirmed_sales": 0,
        "source": "OLX_ACTIVE_ASKING_PRICES",
        "method": "SAME_GPU_RELATED_CPU_EQUAL_RAM",
        "status": "INSUFFICIENT_COMPARABLES",
        "peer_count": 0,
        "asking_p25_minor": None,
        "scenario_sale_minor": None,
        "scenario_profit_minor": None,
        "scenario_max_buy_minor": None,
        "risk_flags": [
            "ASKING_PRICES_NOT_SALES",
            "UNVERIFIED_CONDITION",
            "UNKNOWN_ADDITIONAL_COSTS",
        ],
        "note": (
            "Wynik pogladowy. Nie jest prognoza "
            "potwierdzonych transakcji."
        ),
    }

    if status == "REMOVED":
        return {
            **result,
            "status": "OFFER_REMOVED",
        }

    if (
        category.category != "DESKTOP_PC"
        or not category.pc_pricing_input_complete
    ):
        return {
            **result,
            "status": "NOT_ELIGIBLE",
        }

    if (
        type(price_minor) is not int
        or price_minor <= 0
    ):
        return {
            **result,
            "status": "INVALID_TARGET",
        }

    attrs = category.attributes

    target = hardware_key(
        attrs.get("cpu"),
        attrs.get("gpu"),
        attrs.get("ram_gb"),
    )

    if target is None:
        return {
            **result,
            "status": "INVALID_TARGET",
        }

    target_cpu, target_gpu, target_ram = target

    reference = CPU_REFERENCE.get(target_cpu)

    if reference is None or reference <= 0:
        return {
            **result,
            "status": "CPU_REFERENCE_UNAVAILABLE",
        }

    own = canonical_id(url)
    peers = []

    for row in evidence.rows:
        candidate_cpu, candidate_gpu, candidate_ram = (
            row["key"]
        )

        if (
            candidate_gpu != target_gpu
            or candidate_ram != target_ram
        ):
            continue

        if (
            own is not None
            and row["canonical_id"] == own
        ):
            continue

        candidate_reference = CPU_REFERENCE.get(
            candidate_cpu
        )

        if (
            candidate_reference is None
            or candidate_reference <= 0
        ):
            continue

        # Nie zawyzamy wyceny drozszymi procesorami.
        # Wartosc CPU sluzy tylko do selekcji.
        if not (
            0.85 * reference
            <= candidate_reference
            <= reference
        ):
            continue

        peers.append(row)

    unique = {
        row["canonical_id"]: row
        for row in peers
    }

    peers = list(unique.values())
    result["peer_count"] = len(peers)

    if len(peers) < MIN_PEERS:
        return result

    prices = [
        row["price_minor"]
        for row in peers
    ]

    median = percentile(prices, 0.5)

    peers = [
        row
        for row in peers
        if (
            median * 0.6
            <= row["price_minor"]
            <= median * 1.6
        )
    ]

    result["peer_count"] = len(peers)

    if len(peers) < MIN_PEERS:
        return {
            **result,
            "status": "INSUFFICIENT_AFTER_OUTLIERS",
        }

    prices = [
        row["price_minor"]
        for row in peers
    ]

    p25 = percentile(prices, 0.25)
    q75 = percentile(prices, 0.75)

    if q75 - p25 > median * 0.45:
        return {
            **result,
            "status": "MARKET_TOO_DISPERSED",
        }

    # Orientacyjna cena odsprzedazy:
    # 18% ponizej dolnego kwartylu cen ofertowych.
    sale = (p25 * 82) // 100

    if sale <= 0:
        return {
            **result,
            "status": "INVALID_SCENARIO",
        }

    projection = quote(
        price_minor,
        sale,
        costs={
            "RISK_RESERVE": RESERVE_MINOR,
        },
        confidence="LOW",
        condition="unknown",
    )

    profit = projection[
        "operating_profit_minor"
    ]

    return {
        **result,
        "status": "SCENARIO_REVIEW_ONLY",
        "peer_count": len(peers),
        "asking_p25_minor": p25,
        "scenario_sale_minor": sale,
        "scenario_profit_minor": profit,
        "scenario_max_buy_minor": projection[
            "max_purchase_minor"
        ],
        "risk_reserve_minor": RESERVE_MINOR,
        "review_priority": (
            "HIGH"
            if profit >= 70000
            else "MEDIUM"
            if profit >= 40000
            else "LOW"
        ),
        "risk_flags": result["risk_flags"] + [
            "LEGACY_CPU_REFERENCE",
            "LOW_CONFIDENCE",
        ],
    }
