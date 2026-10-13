from .comparables import estimate


def review(rows, comparable_key, excluded_id=''):

    result = estimate(
        rows,
        comparable_key,
        excluded_id
    )

    independent = {}

    for r in rows:
        if (
            r.key == comparable_key
            and r.source_id != excluded_id
        ):
            independent[r.source_id] = r

    result = dict(result)

    result['independent_sources'] = len(
        independent
    )

    result['confirmed_sales'] = sum(
        1
        for r in independent.values()
        if (
            r.kind == 'SOLD_VERIFIED'
            and bool(r.evidence)
        )
    )

    result['asking_count'] = sum(
        1
        for r in independent.values()
        if r.kind == 'ASKING'
    )

    return result
