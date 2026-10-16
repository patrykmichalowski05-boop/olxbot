"""Ręczny import opisów bez pobierania stron."""

from .model import Listing, PriceKind, minor


def convert(data):
    if not isinstance(data, dict):
        raise ValueError('wymagany slownik')

    allowed = {
        'external_id',
        'title',
        'description',
        'price',
        'price_kind',
        'attributes',
        'quantity',
        'url',
    }

    if set(data) - allowed:
        raise ValueError('nieznane pola w imporcie')

    price = data.get('price')

    kind = PriceKind(
        data.get('price_kind', 'UNKNOWN')
    )

    attrs = data.get('attributes', {})

    if not isinstance(attrs, dict):
        raise ValueError(
            'atrybuty musza byc slownikiem'
        )

    return Listing(
        source='MANUAL',
        external_id=str(
            data.get('external_id', '')
        ).strip(),

        title=str(
            data.get('title', '')
        ).strip(),

        description=str(
            data.get('description', '')
        ),

        price_minor=(
            minor(price)
            if price is not None
            else None
        ),

        price_kind=kind,
        attributes=attrs,
        quantity=data.get('quantity', 1),
        url=data.get('url', ''),
        provenance='user_supplied',
    )
