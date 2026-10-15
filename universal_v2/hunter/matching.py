"""Deterministic matching: prices never substitute for product identity."""

from __future__ import annotations

import re
import unicodedata

from .models import Offer, Search, digest


def normalize(value) -> str:
    value = str(value).lower().translate(str.maketrans({"ł": "l", "đ": "d"}))
    value = re.sub(r"\b((?:[saz]|iphone)\s*\d{1,3})\s*\+", r"\1 plus", value)
    value = "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )
    value = re.sub(
        r"([a-z])(?=\d)|(?<=\d)([a-z])",
        lambda m: (m.group(1) + " ") if m.group(1) else (" " + m.group(2)),
        value,
    )
    value = " ".join(re.findall(r"[a-z0-9]+", value))
    value = re.sub(r"\bpromax\b", "pro max", value)
    return re.sub(r"\btisuper\b", "ti super", value)


def contains(text: str, phrase: str) -> bool:
    return f" {normalize(phrase)} " in f" {text} "



def _complete_system_title(title: str) -> bool:
    """Rozpoznaje kompletny komputer lub laptop zamiast samej karty GPU."""

    normalized = normalize(title)

    system_model = (
        r"\b(?:pc|komputer|laptop|notebook|zestaw komputerowy|"
        r"stacja robocza|workstation|gamingowy komputer|"
        r"lenovo (?:loq|legion|ideapad|thinkpad|yoga)|"
        r"(?:asus )?(?:zenbook|vivobook|rog zephyrus|rog strix g (?:14|15|16|17|18))|"
        r"hp (?:victus|omen|pavilion|envy|zbook)|"
        r"(?:dell )?(?:alienware|inspiron|precision|xps)|"
        r"(?:gigabyte )?aorus (?:15|16|17)(?: [a-z])?|"
        r"msi (?:creator|katana|raider|stealth|cyborg|vector)|"
        r"acer (?:nitro|predator))\b"
    )

    if re.search(system_model, normalized):
        return True

    raw = title.casefold()

    cpu = bool(re.search(
        r"\b(?:i[3579][- ]?\d{4,5}[a-z]{0,2}|"
        r"(?:amd )?ryzen\s*[3579][- ]?\d{4,5}[a-z0-9]{0,3}|"
        r"r[3579][- ]?\d{4,5}[a-z]{0,3}|"
        r"core\s+ultra\s*[3579])\b",
        raw,
    ))

    system_component = bool(re.search(
        r"\b(?:ddr[345]|ram|ssd|nvme|z[679]\d{2}|b[456]\d{2})\b",
        raw,
    ))

    return cpu and system_component


def attributes(offer: Offer) -> dict:
    text = normalize(offer.title + " " + offer.description)
    result = dict(offer.attributes)
    phone = re.search(
        r"\b(iphone \d{1,2}(?: pro max| pro| plus| mini)?|galaxy [saz] \d{1,3}(?: ultra| plus| fe)?)\b",
        text,
    )
    gpu = re.search(r"\b(rtx|gtx|rx) (\d{3,4})(?: (ti super|ti|super|xtx|xt))?\b", text)
    if phone:
        result.setdefault("product_model", phone.group(0))
        capacities = set(re.findall(r"\b(64|128|256|512|1024) gb\b", text))
        if len(capacities) == 1:
            result.setdefault("storage_gb", int(next(iter(capacities))))
        result.setdefault("item_type", "PHONE")
    elif gpu:
        result.setdefault("gpu", " ".join(x for x in gpu.groups() if x))
        # Komputer i laptop nie sa samodzielna karta graficzna.
        full_pc = _complete_system_title(offer.title)
        result.setdefault("item_type", "PC" if full_pc else "GPU")
        if not full_pc:
            title = normalize(offer.title)
            title_gpu = re.search(
                r"\b(rtx|gtx|rx) (\d{3,4})(?: (ti super|ti|super|xtx|xt))?\b",
                title,
            )
            # Jawna pojemność VRAM, a nie przypadkowe 16/32 GB RAM.
            explicit = set()
            for hit in re.finditer(
                r"\b(?:vram|pamiec (?:karty|graficzna)) (?:\d+ )?(4|6|8|10|12|16|20|24|32|48) gb\b"
                r"|\b(4|6|8|10|12|16|20|24|32|48) gb (?:vram|gddr)\b",
                text,
            ):
                explicit.add(int(hit.group(1) or hit.group(2)))
            if title_gpu:
                tail = title[title_gpu.end():]
                after_model = re.match(
                    r"\s*(4|6|8|10|12|16|20|24|32|48) gb(?! (?:ram|ddr))\b",
                    tail,
                )
                if after_model:
                    explicit.add(int(after_model.group(1)))
            if len(explicit) == 1:
                result.setdefault("vram_gb", explicit.pop())
            elif not explicit:
                # Wyłącznie modele desktopowe o stałej, znanej pojemności.
                # RTX 4060 Ti / 5060 Ti mają kilka wariantów i nie mogą
                # otrzymać pamięci z samej nazwy modelu.
                known_desktop_vram = {
                    "rtx 4070": 12,
                    "rtx 4070 super": 12,
                    "rtx 4070 ti": 12,
                    "rtx 4070 ti super": 16,
                }
                known = known_desktop_vram.get(result.get("gpu"))
                if known is not None and "vram_gb" not in result:
                    result["vram_gb"] = known
                    result["vram_source"] = "MODEL_SPEC"
        else:
            from facebook.facebook_specs_parser import parse_pc_specs

            specs = parse_pc_specs(offer.title + " " + offer.description)
            for key in ("cpu", "ram", "disks"):
                if specs.get(key):
                    result.setdefault(key, specs[key])
    if "year" not in result:
        years = set(re.findall(r"\b(?:19[89]\d|20\d{2})\b", text))
        if len(years) == 1:
            result["year"] = int(next(iter(years)))
    if "mileage_km" not in result:
        match = re.search(
            r"\b(\d[\d \u00a0]*)\s*km\b", offer.title + " " + offer.description, re.I
        )
        if match:
            result["mileage_km"] = int(re.sub(r"\s", "", match.group(1)))
    result["condition"] = offer.condition
    return result


def risks(offer: Offer) -> list[str]:
    text = normalize(offer.title)
    result = []
    if offer.price_kind != "FULL":
        result.append("Cena nie jest pełną ceną zakupu")
    if re.search(
        r"\b(uszkodzon\w*|niesprawn\w*|nie dziala|na czesci|(?:puste|samo) pudelko|sam karton|box only|atrapa|odstap\w*|leasing|netto|rata|raty|miesiecznie|zaliczka)\b",
        text,
    ):
        result.append("Możliwe uszkodzenie, akcesorium lub niepełna cena")
    if re.search(r"\b(kupie|szukam|poszukuje|wanted)\b", text):
        result.append("Ogłoszenie może dotyczyć zakupu zamiast sprzedaży")
    if offer.condition == "DAMAGED":
        result.append("Przedmiot uszkodzony")
    description = normalize(offer.description)
    description = re.sub(
        r"\bnie (?:jest |byl |byla )?uszkodzon\w*\b|\bbez uszkodzen\b", "", description
    )
    if re.search(
        r"\b(uszkodzon\w*|niesprawn\w*|nie dziala|na czesci|blokada icloud|zablokowan\w* icloud|artefakty|nie uruchamia sie)\b",
        description,
    ):
        result.append("Opis wskazuje na usterkę lub blokadę wymagającą weryfikacji")
    return result


def matches(offer: Offer, search: Search) -> bool:
    if offer.platform not in search.platforms or offer.currency != "PLN":
        return False
    text = normalize(offer.title + " " + offer.description)
    title = normalize(offer.title)
    terms = search.required_terms or tuple(search.query.split())
    if not all(contains(title, term) for term in terms):
        return False
    if any(contains(text, term) for term in search.excluded_terms):
        return False
    values = attributes(offer)
    query = normalize(search.query)
    expected_gpu = re.search(
        r"\b(rtx|gtx|rx) (\d{3,4})(?: (ti super|ti|super|xtx|xt))?\b", query
    )
    expected_phone = re.search(
        r"\b(iphone \d{1,2}(?: pro max| pro| plus| mini)?|galaxy [saz] \d{1,3}(?: ultra| plus| fe)?)\b",
        query,
    )
    if expected_gpu:
        expected = " ".join(x for x in expected_gpu.groups() if x)
        if normalize(values.get("gpu", "")) != expected:
            return False
        if (
            (values.get("item_type") == "PC" or _complete_system_title(offer.title))
            and not re.search(r"\b(pc|komputer|laptop|notebook)\b", query)
            and search.attributes.get("item_type") != "PC"
        ):
            return False
    if expected_phone and normalize(
        values.get("product_model", "")
    ) != expected_phone.group(0):
        return False
    if expected_phone or expected_gpu:
        accessories = (
            "etui",
            "pokrowiec",
            "folia",
            "szklo ochronne",
            "pudelko",
            "backplate",
            "chlodzenie do",
            "obudowa do",
            "ladowarka do",
            "szklo",
            "case",
            "wentylator",
            "radiator",
        )
        if any(
            contains(title, word) and not contains(query, word) for word in accessories
        ):
            return False
    for key, wanted in search.attributes.items():
        actual = values.get(key)
        if isinstance(wanted, dict):
            if set(wanted) - {"min", "max"} or type(actual) not in (int, float):
                return False
            if "min" in wanted and actual < wanted["min"]:
                return False
            if "max" in wanted and actual > wanted["max"]:
                return False
        elif isinstance(wanted, list):
            if normalize(actual) not in {normalize(value) for value in wanted}:
                return False
        elif actual is None or normalize(actual) != normalize(wanted):
            return False
    return True


def comparable_key(offer: Offer, search: Search) -> str | None:
    if not matches(offer, search) or risks(offer):
        return None
    attrs = attributes(offer)
    required = set(search.variant_keys)
    item_type = attrs.get("item_type")
    if item_type == "PHONE":
        required.update(("product_model", "storage_gb"))
    elif item_type == "GPU":
        required.update(("gpu", "vram_gb"))
    elif item_type == "PC":
        required.update(("cpu", "gpu", "ram", "disks"))
    if search.category == "CAR":
        required.update(("year", "mileage_km", "engine", "gearbox"))
    elif search.category == "FASHION":
        required.update(("style_code", "size"))
    # Unknown product families need explicitly selected variant keys. A title
    # alone cannot distinguish dimensions, kit contents or similar models.
    # Such items still work in the price-limit watch mode.
    if not required:
        return None
    if any(attrs.get(key) in (None, "", "?") for key in required):
        return None
    variants = {
        key: normalize(attrs[key]) if isinstance(attrs[key], str) else attrs[key]
        for key in sorted(required)
    }
    if search.category == "CAR":
        # Mileage is grouped in 20k bands, never discarded from comparisons.
        if (
            type(attrs["mileage_km"]) is not int
            or type(attrs["year"]) is not int
            or attrs["mileage_km"] < 0
        ):
            return None
        variants["mileage_km"] = attrs["mileage_km"] // 20000
    return digest(
        {
            "query": normalize(search.query),
            "category": search.category,
            "condition": offer.condition,
            "type": item_type,
            "variants": variants,
        }
    )
