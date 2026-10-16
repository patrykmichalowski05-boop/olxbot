from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PLATFORMS = ("OLX", "FACEBOOK", "ALLEGRO_LOKALNIE", "OTOMOTO", "VINTED")
HOSTS = {
    "OLX": ("www.olx.pl", "olx.pl"),
    "FACEBOOK": ("www.facebook.com", "facebook.com", "m.facebook.com"),
    "ALLEGRO_LOKALNIE": ("allegrolokalnie.pl", "www.allegrolokalnie.pl"),
    "OTOMOTO": ("www.otomoto.pl", "otomoto.pl"),
    "VINTED": ("www.vinted.pl", "vinted.pl"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise ValueError("Nieprawidłowa data ISO 8601") from None
    if dt.tzinfo is None:
        raise ValueError("Data musi zawierać strefę czasową")
    return dt.astimezone(timezone.utc)


def integer(value: Any, name: str, low: int = 0, high: int = 1_000_000_000) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Nieprawidłowy parametr: {name}")
    return value


def money_input(value: Any) -> int:
    """Parse a major-unit amount; never silently round fractional cents."""
    if value is None or isinstance(value, (bool, float)):
        raise ValueError("Cena musi być tekstem lub liczbą dziesiętną")
    if isinstance(value, (int, Decimal)):
        amount = Decimal(value) * 100
        if not amount.is_finite() or amount != amount.to_integral_value():
            raise ValueError("Cena nie może zawierać ułamka grosza")
        return integer(int(amount), "cena")
    raw = re.sub(r"\s+", "", str(value)).replace("zł", "").replace("PLN", "")
    if not re.fullmatch(r"\d[\d.,]*", raw):
        raise ValueError("Nieprawidłowa cena")
    if "," in raw and "." in raw:
        decimal = "," if raw.rfind(",") > raw.rfind(".") else "."
        grouping = "." if decimal == "," else ","
        whole, fraction = raw.rsplit(decimal, 1)
        if not re.fullmatch(
            r"\d{1,3}(?:" + re.escape(grouping) + r"\d{3})+", whole
        ) or not re.fullmatch(r"\d{1,2}", fraction):
            raise ValueError("Nieprawidłowe separatory ceny")
        raw = whole.replace(grouping, "") + "." + fraction
    elif raw.count(",") == 1:
        raw = raw.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        amount = Decimal(raw) * 100
    except InvalidOperation:
        raise ValueError("Nieprawidłowa cena") from None
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError("Cena nie może zawierać ułamka grosza")
    return integer(int(amount), "cena")


def platform_url(platform: str, value: str) -> str:
    if platform not in HOSTS or not isinstance(value, str):
        raise ValueError("Nieznana platforma lub adres")
    try:
        u = urlsplit(value)
        valid = (
            u.scheme == "https"
            and u.hostname in HOSTS[platform]
            and not u.username
            and not u.password
            and u.port in (None, 443)
        )
    except ValueError:
        valid = False
    if not valid or len(value) > 2048:
        raise ValueError("Adres musi prowadzić do wybranej platformy przez HTTPS")
    # Retain meaningful parameters, remove only tracking and fragments.
    query = [
        (k, v)
        for k, v in parse_qsl(u.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower() not in {"fbclid", "gclid", "ref", "referral_code", "tracking"}
    ]
    host = HOSTS[platform][0]
    return urlunsplit(("https", host, u.path.rstrip("/") or "/", urlencode(query), ""))


def digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class Offer:
    platform: str
    external_id: str
    title: str
    price_minor: int | None
    url: str
    description: str = ""
    currency: str = "PLN"
    attributes: dict = field(default_factory=dict)
    condition: str = "UNKNOWN"
    price_kind: str = "FULL"
    status: str = "ACTIVE"
    image_url: str | None = None
    seller_key: str | None = None
    observed_at: str = field(default_factory=now_iso)
    published_at: str | None = None
    sale_evidence: str | None = None

    def __post_init__(self):
        if self.platform not in PLATFORMS:
            raise ValueError("Nieobsługiwana platforma")
        if (
            not isinstance(self.external_id, str)
            or not 1 <= len(self.external_id) <= 240
        ):
            raise ValueError("Nieprawidłowy identyfikator oferty")
        if not isinstance(self.title, str) or not 1 <= len(self.title.strip()) <= 500:
            raise ValueError("Nieprawidłowy tytuł")
        if not isinstance(self.description, str) or len(self.description) > 20000:
            raise ValueError("Nieprawidłowy opis")
        if self.price_minor is not None:
            integer(self.price_minor, "cena")
        if self.currency not in {"PLN", "EUR", "USD", "GBP"}:
            raise ValueError("Nieobsługiwana waluta")
        if self.condition not in {"NEW", "USED", "REFURBISHED", "DAMAGED", "UNKNOWN"}:
            raise ValueError("Nieprawidłowy stan przedmiotu")
        if self.status not in {"ACTIVE", "SOLD_VERIFIED", "REMOVED"}:
            raise ValueError("Nieprawidłowy stan oferty")
        if self.status == "SOLD_VERIFIED" and not self.sale_evidence:
            raise ValueError("Potwierdzona sprzedaż wymaga dowodu")
        if self.price_kind not in {
            "FULL",
            "INSTALLMENT",
            "NET",
            "DEPOSIT",
            "AUCTION",
            "BUNDLE",
            "UNKNOWN",
        }:
            raise ValueError("Nieprawidłowy rodzaj ceny")
        if not isinstance(self.attributes, dict) or len(self.attributes) > 64:
            raise ValueError("Nieprawidłowe cechy przedmiotu")
        if len(json.dumps(self.attributes, allow_nan=False)) > 20000:
            raise ValueError("Zbyt duży zestaw cech przedmiotu")
        object.__setattr__(self, "url", platform_url(self.platform, self.url))
        object.__setattr__(self, "observed_at", timestamp(self.observed_at).isoformat())
        if self.published_at:
            object.__setattr__(
                self, "published_at", timestamp(self.published_at).isoformat()
            )
        for name in ("seller_key", "sale_evidence"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not 1 <= len(value) <= 500
            ):
                raise ValueError(f"Nieprawidłowy parametr: {name}")
        if self.image_url:
            image = urlsplit(self.image_url)
            if (
                image.scheme != "https"
                or not image.hostname
                or image.username
                or image.password
            ):
                raise ValueError("Nieprawidłowy adres zdjęcia")

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.external_id}"

    def payload(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, row: dict, platform: str | None = None) -> "Offer":
        if not isinstance(row, dict):
            raise ValueError("Oferta musi być obiektem JSON")
        allowed = {f.name for f in fields(cls)}
        data = {k: v for k, v in row.items() if k in allowed}
        if platform:
            if data.get("platform", platform) != platform:
                raise ValueError("Niezgodna platforma w pliku źródła")
            data["platform"] = platform
        if "price_minor" not in data:
            data["price_minor"] = (
                money_input(row["price"]) if row.get("price") is not None else None
            )
        try:
            return cls(**data)
        except TypeError:
            raise ValueError("Brak wymaganych pól oferty") from None


@dataclass(frozen=True)
class Costs:
    shipping_minor: int = 0
    repairs_minor: int = 0
    travel_minor: int = 0
    other_minor: int = 0
    sale_fee_bps: int = 0
    reserve_bps: int = 500

    def __post_init__(self):
        for name in ("shipping_minor", "repairs_minor", "travel_minor", "other_minor"):
            integer(getattr(self, name), name)
        integer(self.sale_fee_bps, "prowizja", 0, 10000)
        integer(self.reserve_bps, "rezerwa", 0, 10000)

    def amounts(self, buy: int, sell: int) -> dict[str, int]:
        return {
            "shipping": self.shipping_minor,
            "repairs": self.repairs_minor,
            "travel": self.travel_minor,
            "other": self.other_minor,
            "sale_fee": (sell * self.sale_fee_bps + 9999) // 10000,
            "reserve": (buy * self.reserve_bps + 9999) // 10000,
        }


@dataclass(frozen=True)
class Search:
    id: str
    owner_id: str
    name: str
    query: str
    platforms: tuple[str, ...] = PLATFORMS
    category: str = "OTHER"
    required_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()
    variant_keys: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)
    source_urls: dict[str, str] = field(default_factory=dict)
    max_price_minor: int | None = None
    min_profit_minor: int = 40000
    min_roi_bps: int = 1500
    min_discount_bps: int = 1500
    min_comparables: int = 5
    reference_days: int = 14
    asking_haircut_bps: int = 1500
    max_spread_bps: int = 5000
    allow_asking_alerts: bool = True
    notify_initial: bool = False
    enabled: bool = True
    purpose: str = "flip"
    costs: Costs = field(default_factory=Costs)

    def __post_init__(self):
        for name, limit in [
            ("id", 80),
            ("owner_id", 120),
            ("name", 120),
            ("query", 150),
        ]:
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
                raise ValueError(f"Nieprawidłowy parametr: {name}")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.id):
            raise ValueError(
                "ID wyszukiwania może zawierać litery, cyfry, kropkę, _ i -"
            )
        if (
            not isinstance(self.platforms, (tuple, list))
            or not self.platforms
            or any(p not in PLATFORMS for p in self.platforms)
            or len(set(self.platforms)) != len(self.platforms)
        ):
            raise ValueError("Nieprawidłowe platformy")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,39}", self.category):
            raise ValueError("Nieprawidłowa kategoria")
        for name in ("required_terms", "excluded_terms", "variant_keys"):
            value = getattr(self, name)
            if (
                not isinstance(value, (list, tuple))
                or len(value) > 32
                or any(not isinstance(v, str) or not 1 <= len(v) <= 100 for v in value)
            ):
                raise ValueError(f"Nieprawidłowy parametr: {name}")
        if not isinstance(self.attributes, dict) or len(self.attributes) > 32:
            raise ValueError("Nieprawidłowe filtry cech")

        def scalar(value):
            return type(value) in (str, int) and (
                type(value) is not str or 0 < len(value) <= 150
            )

        for key, value in self.attributes.items():
            if not isinstance(key, str) or not re.fullmatch(
                r"[a-z][a-z0-9_]{0,49}", key
            ):
                raise ValueError("Nieprawidłowa nazwa cechy")
            if isinstance(value, dict):
                if (
                    not value
                    or set(value) - {"min", "max"}
                    or any(type(v) is not int or v < 0 for v in value.values())
                ):
                    raise ValueError(
                        "Zakres cechy musi zawierać min/max jako nieujemne liczby całkowite"
                    )
                if value.get("min", 0) > value.get("max", 1_000_000_000):
                    raise ValueError("Odwrócony zakres cechy")
            elif isinstance(value, list):
                if not 1 <= len(value) <= 32 or any(not scalar(v) for v in value):
                    raise ValueError("Nieprawidłowe warianty cechy")
            elif not scalar(value):
                raise ValueError("Nieprawidłowa wartość cechy")
        if not isinstance(self.source_urls, dict) or len(self.source_urls) > 5:
            raise ValueError("Nieprawidłowe adresy wyszukiwania")
        for platform, url in self.source_urls.items():
            platform_url(platform, url)
        if self.max_price_minor is not None:
            integer(self.max_price_minor, "budżet")
        integer(self.min_profit_minor, "zysk")
        integer(self.min_roi_bps, "ROI", 0, 100000)
        for name in ("min_discount_bps", "asking_haircut_bps", "max_spread_bps"):
            integer(getattr(self, name), name, 0, 9000)
        integer(self.min_comparables, "liczba porównań", 3, 100)
        integer(self.reference_days, "okres porównań", 1, 90)
        for name in ("allow_asking_alerts", "notify_initial", "enabled"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Parametr {name} musi być logiczny")
        if self.purpose not in {"flip", "cheap"} or (
            self.purpose == "cheap" and self.max_price_minor is None
        ):
            raise ValueError("Tryb cheap wymaga maksymalnej ceny")
        if not isinstance(self.costs, Costs):
            raise ValueError("Nieprawidłowe koszty")

    def payload(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: dict, owner_id: str | None = None) -> "Search":
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(cls)}:
            raise ValueError("Nieznane pola wyszukiwania")
        data = dict(data)
        if owner_id:
            data["owner_id"] = owner_id
        for name in ("platforms", "required_terms", "excluded_terms", "variant_keys"):
            if name in data:
                if not isinstance(data[name], (list, tuple)):
                    raise ValueError(f"Nieprawidłowy parametr: {name}")
                data[name] = tuple(data[name])
        if isinstance(data.get("costs"), dict):
            try:
                data["costs"] = Costs(**data["costs"])
            except TypeError:
                raise ValueError("Nieznane pola kosztów") from None
        try:
            return cls(**data)
        except TypeError:
            raise ValueError("Brak wymaganych pól wyszukiwania") from None
