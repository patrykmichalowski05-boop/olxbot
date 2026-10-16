import json
import re


def normalize_price(value):

    if value is None:
        return None

    if isinstance(
        value,
        (int, float)
    ):

        value = int(value)

        if 100 <= value <= 100000:
            return value

        return None

    text = str(value)

    text = (
        text
        .replace("\xa0", " ")
        .replace("PLN", "")
        .replace("zł", "")
        .replace("zl", "")
        .strip()
    )

    match = re.search(
        r"\d[\d\s]*",
        text
    )

    if not match:
        return None

    number = (
        match.group(0)
        .replace(" ", "")
    )

    try:

        value = int(number)

    except:

        return None

    if 100 <= value <= 100000:
        return value

    return None


# ============================================================
# JSON-LD
# ============================================================

def find_price_in_json(
    data
):

    if isinstance(
        data,
        dict
    ):

        # Najbardziej wiarygodne:
        # Product -> offers -> price

        offers = data.get(
            "offers"
        )

        if isinstance(
            offers,
            dict
        ):

            value = normalize_price(
                offers.get(
                    "price"
                )
            )

            if value:
                return value

        # Niektóre strony mają price bezpośrednio.

        if (
            data.get("@type")
            in [
                "Offer",
                "Product"
            ]
        ):

            value = normalize_price(
                data.get(
                    "price"
                )
            )

            if value:
                return value

        for value in (
            data.values()
        ):

            result = find_price_in_json(
                value
            )

            if result:
                return result

    elif isinstance(
        data,
        list
    ):

        for item in data:

            result = find_price_in_json(
                item
            )

            if result:
                return result

    return None


def price_from_json_ld(
    page
):

    try:

        scripts = page.locator(
            'script[type="application/ld+json"]'
        )

        for i in range(
            scripts.count()
        ):

            try:

                raw = (
                    scripts.nth(i)
                    .text_content()
                )

                if not raw:
                    continue

                data = json.loads(
                    raw
                )

                price = (
                    find_price_in_json(
                        data
                    )
                )

                if price:
                    return price

            except:
                continue

    except:
        pass

    return None


# ============================================================
# META
# ============================================================

def price_from_meta(
    page
):

    selectors = [
        'meta[itemprop="price"]',
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
    ]

    for selector in selectors:

        try:

            element = page.locator(
                selector
            ).first

            if element.count() == 0:
                continue

            value = (
                element.get_attribute(
                    "content"
                )
            )

            price = normalize_price(
                value
            )

            if price:
                return price

        except:
            continue

    return None


# ============================================================
# OLX PRICE ELEMENT
# ============================================================

def price_from_dom(
    page
):

    selectors = [
        '[data-testid="ad-price-container"]',
        '[data-cy="ad-price-container"]',
        '[data-testid="ad-price"]',
        '[data-cy="ad-price"]',
    ]

    for selector in selectors:

        try:

            element = page.locator(
                selector
            ).first

            if element.count() == 0:
                continue

            text = (
                element.inner_text(
                    timeout=1500
                )
            )

            price = normalize_price(
                text
            )

            if price:
                return price

        except:
            continue

    return None


# ============================================================
# PUBLIC API
# ============================================================

def resolve_offer_price(
    page,
    card_price=None,
    details=None
):
    """
    Priorytet:

    1. cena z karty wyników OLX
    2. cena z offer_parser
    3. JSON-LD
    4. meta tags
    5. element DOM OLX
    """

    # 1. FEED

    price = normalize_price(
        card_price
    )

    if price:

        return {
            "price": price,
            "source": "CARD"
        }

    # 2. PARSER

    if details:

        price = normalize_price(
            details.get(
                "price"
            )
        )

        if price:

            return {
                "price": price,
                "source": "PARSER"
            }

    # 3. JSON-LD

    price = price_from_json_ld(
        page
    )

    if price:

        return {
            "price": price,
            "source": "JSON_LD"
        }

    # 4. META

    price = price_from_meta(
        page
    )

    if price:

        return {
            "price": price,
            "source": "META"
        }

    # 5. DOM

    price = price_from_dom(
        page
    )

    if price:

        return {
            "price": price,
            "source": "DOM"
        }

    return {
        "price": None,
        "source": "NOT_FOUND"
    }
