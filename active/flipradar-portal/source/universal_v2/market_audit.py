"""Kontrola porownan i identyfikator wersji rynku."""

from dataclasses import asdict

from .comparables import estimate
from .evidence import permitted_comparables
from .revision import fingerprint


def review_market(
    samples, policies,
    comparable_key,
    excluded_id=''
):
    allowed = permitted_comparables(samples, policies)

    unique = {}

    for item in allowed:
        if (
            item.source_id == excluded_id
            or item.key != comparable_key
        ):
            continue

        key = (item.source_id, item.key)
        before = unique.get(key)

        if (
            before is None
            or (
                before.kind == 'ASKING'
                and item.kind == 'SOLD_VERIFIED'
            )
        ):
            unique[key] = item

    cleaned = list(unique.values())

    result = dict(
        estimate(cleaned, comparable_key)
    )

    evidence = sorted(
        [asdict(x) for x in cleaned],
        key=lambda x: (
            x['source_id'],
            x['kind']
        )
    )

    result['market_id'] = fingerprint(evidence)
    result['independent_observations'] = len(cleaned)

    result['verified_sales'] = sum(
        x.kind == 'SOLD_VERIFIED'
        for x in cleaned
    )

    result['asking_prices'] = sum(
        x.kind == 'ASKING'
        for x in cleaned
    )

    return result
