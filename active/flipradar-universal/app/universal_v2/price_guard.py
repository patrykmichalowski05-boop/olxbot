import re

from .model import PriceKind


_BAD = re.compile(
    r'\b('
    r'rat[ay]|'
    r'miesiecznie|miesięcznie|'
    r'odstępne|odstepne|'
    r'leasing|'
    r'zaliczk[ai]|'
    r'netto'
    r')\b',
    re.I
)


def check(row):
    reasons = []

    if row.price_kind != PriceKind.FULL:
        reasons.append('NOT_FULL_PRICE')

    if (
        row.price_minor is None
        or row.price_minor <= 0
    ):
        reasons.append(
            'INVALID_OR_MISSING_PRICE'
        )

    if row.quantity != 1:
        reasons.append(
            'BUNDLE_OR_MULTIPLE_UNITS'
        )

    if _BAD.search(row.title):
        reasons.append(
            'PAYMENT_TYPE_CONFLICT'
        )

    return {
        'ok': not reasons,
        'reasons': reasons,
    }
