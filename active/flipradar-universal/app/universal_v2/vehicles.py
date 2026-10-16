import re

from .electronics import Identity
from .model import Listing, PriceKind


def classify_car(row: Listing):
    title = ' '.join(
        row.title.upper().split()
    )

    attrs = row.attributes
    warnings = []

    models = (
        ('TESLA', 'MODEL 3'),
        ('TESLA', 'MODEL Y'),
        ('BMW', 'I4'),
        ('BMW', '3'),
        ('VOLKSWAGEN', 'TIGUAN'),
        ('SKODA', 'OCTAVIA'),
        ('AUDI', 'A4'),
    )

    found = [
        (brand, model)
        for brand, model in models
        if (
            brand in title
            and re.search(
                r'\b' + re.escape(model) + r'\b',
                title,
            )
        )
    ]

    if len(found) != 1:
        return Identity(
            'CAR',
            '',
            '',
            None,
            ('UNKNOWN_OR_AMBIGUOUS_MODEL',),
        )

    brand, model = found[0]

    year = attrs.get('year')
    mileage = attrs.get('mileage_km')
    generation = attrs.get('generation')
    motor = attrs.get('motor')
    gearbox = attrs.get('gearbox')

    if (
        type(year) is not int
        or year < 1990
        or year > 2100
    ):
        warnings.append('YEAR_UNKNOWN')

    if (
        type(mileage) is not int
        or mileage < 0
    ):
        warnings.append('MILEAGE_UNKNOWN')

    if not generation:
        warnings.append('GENERATION_UNKNOWN')

    if row.price_kind != PriceKind.FULL:
        warnings.append(
            'NOT_TOTAL_PURCHASE_PRICE'
        )

    if brand == 'TESLA':
        drive = str(
            attrs.get(
                'drive_variant',
                '',
            )
        ).upper()

        chemistry = str(
            attrs.get(
                'battery_chemistry',
                '',
            )
        ).upper()

        if drive not in (
            'RWD',
            'LONG_RANGE',
            'PERFORMANCE',
        ):
            warnings.append('DRIVE_UNKNOWN')

        if chemistry not in (
            'LFP',
            'NMC',
            'NCA',
        ):
            warnings.append('BATTERY_UNKNOWN')

        motor = drive + ' ' + chemistry

    elif not motor or not gearbox:
        warnings.append(
            'MOTOR_OR_GEARBOX_UNKNOWN'
        )

    variant = (
        f'{generation} {year} '
        f'{motor} {gearbox or ""}'
    ).strip()

    key = (
        f'CAR:{brand}:{model}:{variant}'
        if not warnings
        else None
    )

    return Identity(
        'CAR',
        brand + ' ' + model,
        variant,
        key,
        tuple(warnings),
    )
