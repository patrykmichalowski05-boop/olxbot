import json
import re
from decimal import Decimal, InvalidOperation


def walk_objects(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def text_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("text")
    return None


def amount_value(value):
    if not isinstance(value, dict):
        return None
    try:
        amount = Decimal(str(value.get("amount")))
        if not amount.is_finite() or amount < 0:
            return None
        return int(amount) if amount == amount.to_integral_value() else float(amount)
    except (InvalidOperation, ValueError, TypeError):
        return None


def extract_from_script(script, listing_id=None):
    if not listing_id:
        return {}

    try:
        payload = json.loads(script)
    except (ValueError, TypeError):
        return {}

    candidates = [
        obj for obj in walk_objects(payload)
        if str(obj.get("id")) == str(listing_id)
        and isinstance(obj.get("listing_price"), dict)
    ]

    if not candidates:
        return {}

    # Preferuj pełny obiekt szczegółów tego samego ogłoszenia.
    obj = max(
        candidates,
        key=lambda item: (
            bool(text_value(item.get("redacted_description"))),
            bool(item["listing_price"].get("currency")),
            len(item),
        ),
    )

    price = obj["listing_price"]
    currency = price.get("currency")

    return {
        "listing_id": str(listing_id),
        "title": obj.get("marketplace_listing_title"),
        "description": text_value(obj.get("redacted_description")),
        "location": text_value(obj.get("location_text")),
        "price": amount_value(price),
        "currency": currency.upper() if isinstance(currency, str) else None,
        "old_price": amount_value(obj.get("strikethrough_price")),
        "creation_time": obj.get("creation_time"),
        "delivery_types": obj.get("delivery_types") or [],
        "is_live": obj.get("is_live"),
        "is_sold": obj.get("is_sold"),
        "is_pending": obj.get("is_pending"),
    }


def extract_detail_metadata(page):
    match = re.search(r"/marketplace/item/(\+?\d+)(?:[/?#]|$)", page.url)
    if not match:
        return {}

    listing_id = match.group(1)
    best = {}
    best_score = (-1, -1, -1)

    for script in page.locator("script").all_text_contents():
        if '"listing_price"' not in script:
            continue

        data = extract_from_script(script, listing_id)
        if not data:
            continue

        score = (
            bool(data.get("description")),
            bool(data.get("currency")),
            data.get("price") is not None,
        )
        if score > best_score:
            best = data
            best_score = score

    return best
