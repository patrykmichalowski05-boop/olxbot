from dataclasses import dataclass
from statistics import median

from .model import assert_minor


@dataclass(frozen=True)
class Comparable:
    key: str
    source_id: str
    price_minor: int
    kind: str
    evidence: str = ''

    def __post_init__(self):
        assert_minor(self.price_minor)

        if self.kind not in (
            'SOLD_VERIFIED',
            'ASKING',
        ):
            raise ValueError(
                'Rodzaj porównania'
            )

        if (
            self.kind == 'SOLD_VERIFIED'
            and not self.evidence
        ):
            raise ValueError(
                'Brak dowodu sprzedaży'
            )


def estimate(
    comparables,
    key,
    excluded_id='',
):
    if not key:
        return {
            'status': 'NO_RELIABLE_VALUATION',
            'reason': 'UNKNOWN_VARIANT',
        }

    independent = {}

    for c in comparables:
        if (
            c.key != key
            or c.source_id == excluded_id
            or c.price_minor <= 0
        ):
            continue

        if (
            c.source_id not in independent
            or (
                c.kind == 'SOLD_VERIFIED'
                and independent[
                    c.source_id
                ].kind != 'SOLD_VERIFIED'
            )
        ):
            independent[c.source_id] = c

    sold = sorted(
        c.price_minor
        for c in independent.values()
        if c.kind == 'SOLD_VERIFIED'
    )

    asking = sorted(
        c.price_minor
        for c in independent.values()
        if c.kind == 'ASKING'
    )

    if len(sold) < 3:
        return {
            'status': 'NO_RELIABLE_VALUATION',
            'reason': 'NOT_ENOUGH_CONFIRMED_SALES',
            'sales': len(sold),
            'asking': len(asking),
        }

    centre = int(median(sold))

    filtered = [
        p
        for p in sold
        if centre // 2 <= p <= centre * 2
    ]

    if len(filtered) < 3:
        return {
            'status': 'NO_RELIABLE_VALUATION',
            'reason': 'TOO_FEW_COMPARABLE_SALES',
        }

    sorted_prices = sorted(filtered)

    low = sorted_prices[
        max(
            0,
            len(filtered) // 4 - 1,
        )
    ]

    high = sorted_prices[
        min(
            len(filtered) - 1,
            3 * len(filtered) // 4,
        )
    ]

    return {
        'status': 'OK',
        'low_minor': low,
        'base_minor': int(
            median(filtered)
        ),
        'high_minor': high,
        'sales': len(filtered),
        'asking': len(asking),
        'confidence': 'MEDIUM',
    }
