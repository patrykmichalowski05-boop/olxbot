"""Pure operational-profit calculator; no taxes included."""

from .ledger import COST_KINDS
from .money import valid_minor
from .policy import FlipPolicy


def quote(
    purchase_minor,
    sale_minor,
    costs=None,
    policy=None,
    *,
    confidence="LOW",
    condition="unknown",
):
    valid_minor(purchase_minor, positive=True)
    valid_minor(sale_minor, positive=True)

    policy = policy or FlipPolicy()
    costs = costs or {}

    if not isinstance(costs, dict):
        raise ValueError("Koszty musza byc slownikiem")

    total_cost = 0

    for kind, amount in costs.items():
        if kind not in COST_KINDS:
            raise ValueError("Nieznany koszt: " + str(kind))

        valid_minor(amount)
        total_cost += amount

    invested = purchase_minor + total_cost
    profit = sale_minor - invested

    roi_bps = (
        profit * 10000 // invested
    )

    max_by_profit = (
        sale_minor
        - total_cost
        - policy.min_profit_minor
    )

    max_by_roi = (
        sale_minor * 10000
        // (10000 + policy.min_roi_bps)
        - total_cost
    )

    max_buy = min(max_by_profit, max_by_roi)

    if policy.max_purchase_minor:
        max_buy = min(
            max_buy,
            policy.max_purchase_minor,
        )

    max_buy = max(0, max_buy)

    return {
        "purchase_minor": purchase_minor,
        "sale_minor": sale_minor,
        "total_cost_minor": total_cost,
        "total_investment_minor": invested,
        "operating_profit_minor": profit,
        "roi_bps": roi_bps,
        "max_purchase_minor": max_buy,
        "decision": policy.decide(
            purchase_minor,
            profit,
            confidence=confidence,
            condition=condition,
        ),
        "policy_version": policy.version,
        "profit_after_tax": False,
    }
