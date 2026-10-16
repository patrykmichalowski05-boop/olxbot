"""Parse public page content; no private endpoints or JavaScript evaluation."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import Offer, digest, money_input, platform_url

LINK_PARTS = {
    "OLX": "/d/oferta/",
    "FACEBOOK": "/marketplace/item/",
    "ALLEGRO_LOKALNIE": "/oferta/",
    "OTOMOTO": "/oferta/",
    "VINTED": "/items/",
}
CARDS = {
    "OLX": '[data-cy="l-card"]',
    "OTOMOTO": '[data-testid="listing-ad"], article[data-id]',
    "ALLEGRO_LOKALNIE": 'article, [data-testid="offer-card"], [data-role="offer"]',
    "FACEBOOK": 'a[href*="/marketplace/item/"]',
    "VINTED": '[data-testid="grid-item"], .feed-grid__item, [data-testid*="item-box"]',
}
PRICE = re.compile(r"(\d[\d\s\u00a0.,]*?)\s*(zł\b|PLN\b|EUR\b|€)", re.I)
EMPTY = re.compile(
    r"nie znaleziono (?:ofert|ogłoszeń|ogloszen|wyników)|brak wyników|no results|no listings found",
    re.I,
)


class SourceError(RuntimeError):
    def __init__(self, code: str, message: str, retry_after: int = 0):
        super().__init__(message)
        self.code, self.retry_after = code, retry_after


def external_id(platform: str, url: str) -> str:
    path = urlsplit(url).path
    patterns = {
        "OLX": r"-(ID[a-zA-Z0-9]+)(?:\.html)?$",
        "OTOMOTO": r"-(ID[a-zA-Z0-9]+)(?:\.html)?$",
        "FACEBOOK": r"/marketplace/item/(\d+)",
        "VINTED": r"/items/(\d+)",
    }
    match = re.search(patterns.get(platform, r"(?!)"), path)
    return (
        match.group(1) if match else digest({"platform": platform, "path": path})[:32]
    )


def _walk(value, depth=0):
    if depth > 32:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value[:5000]:
            yield from _walk(child, depth + 1)


def _condition(value) -> str:
    text = str(value or "").lower()
    if any(word in text for word in ("damaged", "uszkodzon", "forparts")):
        return "DAMAGED"
    if any(word in text for word in ("refurbished", "odnowion")):
        return "REFURBISHED"
    if any(
        word in text
        for word in ("usedcondition", "używan", "uzywan", "bardzo dobry", "very good")
    ):
        return "USED"
    if any(
        word in text for word in ("newcondition", "brand new", "nowy", "nowe", "nowa")
    ):
        return "NEW"
    return "UNKNOWN"


def _kind(text: str) -> str:
    text = text.lower()
    for pattern, kind in [
        (r"\blicytac|\bauction\b", "AUCTION"),
        (r"\bnetto\b", "NET"),
        (r"\bleasing|\bodst[eę]pne|\bzaliczk", "DEPOSIT"),
        (r"\b(?:rata|raty|miesięcznie|miesiecznie)\b", "INSTALLMENT"),
    ]:
        if re.search(pattern, text):
            return kind
    return "FULL"


def _image(value):
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl")
    return value if isinstance(value, str) and value.startswith("https://") else None


def _json_offer(node: dict, platform: str, page_url: str) -> Offer | None:
    name = node.get("name") or node.get("title")
    price = node.get("offers") or node.get("price")
    if not isinstance(name, str) or price is None:
        return None
    if isinstance(price, list):
        price = price[0] if len(price) == 1 else None
    if price is None:
        return None
    meta = price if isinstance(price, dict) else {}
    if "lowPrice" in meta and "price" not in meta:
        return None  # An aggregate "from" price is not a concrete asking price.
    amount = meta.get("price", meta.get("amount", meta.get("value"))) if meta else price
    if isinstance(amount, dict):
        amount = amount.get("amount")
    url = node.get("url") or node.get("href") or meta.get("url")
    if isinstance(url, dict):
        url = url.get("url")
    if not isinstance(url, str) or LINK_PARTS[platform] not in url:
        return None
    try:
        url = platform_url(platform, urljoin(page_url, url))
        attrs = {}
        for key in (
            "brand",
            "model",
            "vehicleModelDate",
            "vehicleTransmission",
            "fuelType",
        ):
            value = node.get(key)
            if isinstance(value, dict):
                value = value.get("name")
            if isinstance(value, (str, int)):
                attrs[
                    {"vehicleModelDate": "year", "vehicleTransmission": "gearbox"}.get(
                        key, key
                    )
                ] = value
        for prop in (
            node.get("additionalProperty", [])
            if isinstance(node.get("additionalProperty", []), list)
            else []
        ):
            if (
                isinstance(prop, dict)
                and isinstance(prop.get("name"), str)
                and isinstance(prop.get("value"), (str, int))
            ):
                attrs[prop["name"][:80]] = prop["value"]
        availability = str(meta.get("availability", ""))
        return Offer(
            platform=platform,
            external_id=external_id(platform, url),
            title=name.strip()[:500],
            price_minor=money_input(amount),
            url=url,
            currency=str(
                meta.get(
                    "priceCurrency", meta.get("currency", node.get("currency", "PLN"))
                )
            ).upper(),
            description=BeautifulSoup(
                str(node.get("description", "")), "html.parser"
            ).get_text(" ", strip=True)[:20000],
            condition=_condition(node.get("itemCondition") or node.get("condition")),
            attributes=attrs,
            image_url=_image(node.get("image") or node.get("photo")),
            price_kind=_kind(name),
            status="REMOVED"
            if any(x in availability for x in ("OutOfStock", "Discontinued", "SoldOut"))
            else "ACTIVE",
        )
    except (ValueError, TypeError):
        return None


def _card_offer(card, platform: str, page_url: str) -> Offer | None:
    link = (
        card
        if card.name == "a" and LINK_PARTS[platform] in str(card.get("href"))
        else card.select_one(f'a[href*="{LINK_PARTS[platform]}"]')
    )
    if link is None:
        return None
    try:
        url = platform_url(platform, urljoin(page_url, link.get("href", "")))
    except ValueError:
        return None
    # A card link may need its containing element to include the visible price.
    node = card
    for _ in range(5):
        text = node.get_text(" ", strip=True)
        if PRICE.search(text):
            break
        parent = node.parent
        if parent is None or parent.name in ("body", "html"):
            break
        links = {
            a.get("href", "").split("?")[0]
            for a in parent.select(f'a[href*="{LINK_PARTS[platform]}"]')
        }
        if len(links) > 1:
            break
        node = parent
    # Crossed-out original prices must not replace the current asking price.
    node = BeautifulSoup(str(node), "html.parser")
    for struck in node.select("del, s"):
        struck.decompose()
    title_node = node.select_one(
        'h1, h2, h3, h4, h5, h6, [data-testid="offer-title"], [data-testid="ad-title"]'
    )
    title = (
        title_node.get_text(" ", strip=True)
        if title_node
        else link.get("title")
        or link.get("aria-label")
        or link.get_text(" ", strip=True)
    )
    if not title:
        image = node.select_one("img[alt]")
        title = image.get("alt", "") if image else ""
    price_node = node.select_one(
        '[data-testid="ad-price"], [data-testid*="price"], [itemprop="price"], .price'
    )
    text = node.get_text(" ", strip=True)
    price_text = (
        price_node.get("content") or price_node.get_text(" ", strip=True)
        if price_node
        else text
    )
    price_match = PRICE.search(price_text)
    currency = (
        "EUR" if price_match and price_match.group(2).upper() in ("EUR", "€") else "PLN"
    )
    try:
        price = (
            money_input(price_match.group(1) if price_match else price_text)
            if price_node or price_match
            else None
        )
    except ValueError:
        price = None
    title = PRICE.sub("", title).strip(" ·-|")
    if not title or price is None:
        return None
    image = node.select_one("img")
    image_url = image.get("src") or image.get("data-src") if image else None
    return Offer(
        platform=platform,
        external_id=external_id(platform, url),
        title=title[:500],
        price_minor=price,
        url=url,
        currency=currency,
        description=text[:20000],
        image_url=_image(image_url),
        condition=_condition(text),
        price_kind=_kind(text),
    )


def parse_page(html: str, platform: str, page_url: str) -> list[Offer]:
    platform_url(platform, page_url)
    if not isinstance(html, str) or len(html.encode()) > 6_000_000:
        raise SourceError("INVALID_RESPONSE", "Nieprawidłowy rozmiar odpowiedzi źródła")
    soup = BeautifulSoup(html, "html.parser")
    offers = {}
    for script in soup.select(
        'script[type="application/ld+json"], script#__NEXT_DATA__'
    ):
        try:
            data = json.loads(script.string or script.get_text(), parse_float=Decimal)
        except (json.JSONDecodeError, ValueError):
            continue
        for node in _walk(data):
            row = _json_offer(node, platform, page_url)
            if row:
                offers[row.key] = row
    for card in soup.select(CARDS[platform]):
        row = _card_offer(card, platform, page_url)
        if row and row.key not in offers:
            offers[row.key] = row
    if not offers:
        for link in soup.select(f'a[href*="{LINK_PARTS[platform]}"]')[:500]:
            row = _card_offer(link, platform, page_url)
            if row:
                offers[row.key] = row
    if offers:
        return list(offers.values())[:300]
    text = soup.get_text(" ", strip=True)
    if soup.select_one(
        'iframe[src*="captcha"], #challenge-running, #cf-challenge-running'
    ) or re.search(
        r"verify (?:that )?you are human|sprawdź, czy jesteś człowiekiem|access denied|automated (?:requests|queries)",
        text,
        re.I,
    ):
        raise SourceError("ACCESS_BLOCKED", "Źródło wymaga ręcznej weryfikacji dostępu")
    if soup.select_one('form[action*="login"]') or "/login" in str(
        soup.find("link", rel="canonical")
    ):
        raise SourceError("LOGIN_REQUIRED", "Źródło wymaga aktywnej sesji użytkownika")
    if EMPTY.search(text):
        return []
    raise SourceError(
        "PARSER_CHANGED",
        "Nie rozpoznano listy ofert. Źródło może wymagać sesji lub aktualizacji adaptera",
    )
