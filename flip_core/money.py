from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_PLN = Decimal("10000000")


def to_minor(value, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise ValueError("Nieprawidlowa kwota")

    try:
        number = Decimal(
            str(value).strip().replace(",", ".")
        )
    except (InvalidOperation, ValueError):
        raise ValueError("Nieprawidlowa kwota") from None

    if (
        not number.is_finite()
        or number < 0
        or number > MAX_PLN
    ):
        raise ValueError("Kwota poza zakresem")

    minor = int(
        (number * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

    if positive and minor <= 0:
        raise ValueError("Kwota musi byc dodatnia")

    return minor


def from_minor(value):
    valid_minor(value)
    return f"{value // 100}.{value % 100:02d}"


def valid_minor(value, *, positive=False):
    if (
        type(value) is not int
        or value < 0
        or value > 1_000_000_000
    ):
        raise ValueError("Wymagana liczba groszy")

    if positive and value == 0:
        raise ValueError("Kwota musi byc dodatnia")

    return value
