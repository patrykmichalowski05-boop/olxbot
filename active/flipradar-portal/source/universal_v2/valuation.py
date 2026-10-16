from .model import assert_minor, Decision


def calculate(
    buy_minor,
    sell_minor,
    costs,
    min_profit_minor=0,
):
    assert_minor(buy_minor)
    assert_minor(sell_minor)
    assert_minor(min_profit_minor)

    if not isinstance(costs, dict):
        raise ValueError(
            'Niepoprawne koszty'
        )

    for name, value in costs.items():
        if not isinstance(name, str):
            raise ValueError(
                'Koszt bez nazwy'
            )

        assert_minor(value)

    total = sum(costs.values())

    invested = buy_minor + total
    profit = sell_minor - invested

    roi_basis_points = (
        profit * 10000 // invested
        if invested
        else 0
    )

    ceiling = (
        sell_minor
        - total
        - min_profit_minor
    )

    return {
        'buy_minor': buy_minor,
        'sell_minor': sell_minor,
        'cost_minor': total,
        'profit_minor': profit,
        'roi_bps': roi_basis_points,
        'max_buy_minor': max(
            0,
            ceiling,
        ),
        'affordable': (
            ceiling >= buy_minor
            and profit >= 0
        ),
        'profit_after_tax': False,
    }


def decide(
    market,
    calc,
    profile,
):
    if market.get('status') != 'OK':
        return (
            Decision.NO_RELIABLE_VALUATION.value
        )

    if not calc['affordable']:
        return Decision.WATCH.value

    if (
        calc['profit_minor']
        >= profile['min_profit_minor']
        and calc['roi_bps']
        >= profile['min_roi_bps']
    ):
        return Decision.BUY_CANDIDATE.value

    return Decision.REVIEW.value
