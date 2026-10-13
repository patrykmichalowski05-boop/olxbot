from .electronics import Identity
from .model import Listing, PriceKind


def classify_fashion(row: Listing):
    a = row.attributes

    brand = str(
        a.get('brand', '')
    ).strip().upper()

    model = str(
        a.get('model', '')
    ).strip().upper()

    size = str(
        a.get('size', '')
    ).strip().upper()

    style = str(
        a.get('style_code', '')
    ).strip().upper()

    condition = str(
        a.get('condition', '')
    ).strip().upper()

    issues = []

    if not all((
        brand,
        model,
        size,
    )):
        issues.append(
            'BRAND_MODEL_SIZE_REQUIRED'
        )

    if not style:
        issues.append(
            'STYLE_CODE_MISSING'
        )

    if condition not in (
        'NEW',
        'VERY_GOOD',
        'GOOD',
        'USED',
    ):
        issues.append(
            'CONDITION_UNKNOWN'
        )

    if row.price_kind != PriceKind.FULL:
        issues.append(
            'PRICE_NOT_FULL'
        )

    if a.get('authenticity') != 'verified':
        issues.append(
            'AUTHENTICITY_UNVERIFIED'
        )

    key = (
        f'FASHION:{brand}:{model}:'
        f'{style}:{size}:{condition}'
        if not issues
        else None
    )

    return Identity(
        'FASHION',
        brand + ' ' + model,
        size + ' ' + style,
        key,
        tuple(issues),
    )
