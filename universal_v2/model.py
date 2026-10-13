from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from urllib.parse import urlsplit


class PriceKind(str, Enum):
    FULL = 'FULL'
    NET = 'NET'
    INSTALLMENT = 'INSTALLMENT'
    DEPOSIT = 'DEPOSIT'
    LEASE = 'LEASE'
    BUNDLE = 'BUNDLE'
    UNKNOWN = 'UNKNOWN'


class Decision(str, Enum):
    BUY_CANDIDATE = 'BUY_CANDIDATE'
    NEGOTIATE = 'NEGOTIATE'
    REVIEW = 'REVIEW'
    WATCH = 'WATCH'
    SKIP = 'SKIP'
    NO_RELIABLE_VALUATION = 'NO_RELIABLE_VALUATION'


def minor(value):
    if isinstance(value, (float, bool)) or value is None:
        raise ValueError(
            'Kwota musi być tekstem lub int'
        )

    try:
        number = Decimal(
            str(value).replace(',', '.').strip()
        )
    except (InvalidOperation, ValueError):
        raise ValueError(
            'Nieprawidłowa kwota'
        ) from None

    if (
        not number.is_finite()
        or number < 0
        or number > 10_000_000
    ):
        raise ValueError(
            'Kwota poza zakresem'
        )

    cents = number * 100

    if cents != cents.to_integral_value():
        raise ValueError(
            'Ułamki groszy niedozwolone'
        )

    return int(cents)


def assert_minor(value):
    if (
        type(value) is not int
        or not 0 <= value <= 1_000_000_000
    ):
        raise ValueError(
            'Nieprawidłowe grosze'
        )


def utc(value=None):
    if value is None:
        return datetime.now(
            timezone.utc
        ).isoformat()

    try:
        dt = datetime.fromisoformat(
            value.replace('Z', '+00:00')
        )
    except (AttributeError, ValueError):
        raise ValueError(
            'Nieprawidłowa data'
        ) from None

    if dt.tzinfo is None:
        raise ValueError(
            'Data bez strefy'
        )

    return dt.astimezone(
        timezone.utc
    ).isoformat()


@dataclass(frozen=True)
class Listing:
    source: str
    external_id: str
    title: str
    price_minor: int | None

    price_kind: PriceKind = PriceKind.UNKNOWN
    currency: str = 'PLN'
    description: str = ''
    url: str = ''

    attributes: dict = field(
        default_factory=dict
    )

    provenance: str = 'user_supplied'
    quantity: int = 1

    observed_at: str = field(
        default_factory=utc
    )

    def __post_init__(self):
        required = (
            self.source,
            self.external_id,
            self.title,
        )

        if not all(
            isinstance(v, str) and v.strip()
            for v in required
        ):
            raise ValueError(
                'Brak wymaganych pól'
            )

        if (
            len(self.title) > 500
            or len(self.description) > 20000
        ):
            raise ValueError(
                'Za długi opis'
            )

        if self.price_minor is not None:
            assert_minor(self.price_minor)

        if not isinstance(
            self.price_kind,
            PriceKind,
        ):
            raise ValueError(
                'Zły typ ceny'
            )

        if self.currency not in (
            'PLN',
            'EUR',
            'USD',
            'GBP',
        ):
            raise ValueError(
                'Nieobsługiwana waluta'
            )

        if self.provenance not in (
            'user_supplied',
            'licensed_feed',
            'first_party',
        ):
            raise ValueError(
                'Nieznane pochodzenie'
            )

        if (
            type(self.quantity) is not int
            or not 1 <= self.quantity <= 1000
        ):
            raise ValueError(
                'Zła ilość'
            )

        if not isinstance(
            self.attributes,
            dict,
        ):
            raise ValueError(
                'Złe cechy'
            )

        if self.url:
            u = urlsplit(self.url)

            if (
                u.scheme != 'https'
                or not u.hostname
                or u.username
                or u.password
            ):
                raise ValueError(
                    'Adres musi być HTTPS'
                )

        object.__setattr__(
            self,
            'observed_at',
            utc(self.observed_at),
        )
