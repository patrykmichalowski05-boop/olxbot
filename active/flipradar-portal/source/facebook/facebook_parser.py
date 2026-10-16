import re


PRICE_RE = re.compile(
    r"^\s*([\d\s.,]+)\s*zł\s*$",
    re.I
)


def parse_price(text):
    if not text:
        return None

    match = PRICE_RE.match(
        text.strip()
    )

    if not match:
        return None

    value = match.group(1)

    value = (
        value
        .replace(" ", "")
        .replace("\xa0", "")
        .replace(",", ".")
    )

    try:
        return int(
            float(value)
        )
    except ValueError:
        return None


def parse_marketplace_card(text):

    if not text:
        return None

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    prices = []
    other_lines = []

    for line in lines:

        price = parse_price(
            line
        )

        if price is not None:
            prices.append(
                price
            )
        else:
            other_lines.append(
                line
            )

    current_price = (
        prices[0]
        if prices
        else None
    )

    old_price = (
        prices[1]
        if len(prices) >= 2
        else None
    )

    title = None
    location = None

    if len(other_lines) >= 2:

        location = (
            other_lines[-1]
        )

        title = " ".join(
            other_lines[:-1]
        )

    elif len(other_lines) == 1:

        title = (
            other_lines[0]
        )

    return {
        "price":
            current_price,

        "old_price":
            old_price,

        "title":
            title,

        "location":
            location,

        "raw_lines":
            lines,
    }
