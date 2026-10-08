import re
import unicodedata

GPU_RE = re.compile(
    r"\b(RTX|GTX|RX)\s*-?\s*(\d{3,4})"
    r"(?:[\s-]*(SUPER|XTX|TI|XT))?\b",
    re.I,
)

RAM_PATTERNS = (
    r"\b(\d{1,3})\s*GB?\s*(?:RAM|DDR[345])\b",
    r"\b(?:RAM|DDR[345])\s*[:/-]?\s*(\d{1,3})\s*GB?\b",
)

def field(row, key):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None

def norm(value):
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )
    return text.upper().strip()

def gpu_models(text):
    return {
        (m.group(1).upper(), m.group(2),
         (m.group(3) or "").upper())
        for m in GPU_RE.finditer(norm(text))
    }

def ram_values(text):
    text = norm(text)
    values = set()
    for pattern in RAM_PATTERNS:
        for match in re.finditer(pattern, text):
            value = int(match.group(1))
            if value in (8, 12, 16, 24, 32, 48, 64, 96, 128):
                values.add(value)
    return values


def is_placeholder_title(value):
    return norm(value) in {
        "",
        "DOSTAWA GRATIS",
        "DARMOWA DOSTAWA",
        "WYSYLKA GRATIS",
        "ODBIOR OSOBISTY",
        "PROMOWANE",
        "WYROZNIONE",
        "KUP Z PRZESYLKA",
    }


def select_market_card_title(card_text):
    for line in str(card_text or "").splitlines():
        candidate = line.strip()

        if is_placeholder_title(candidate):
            continue

        if len(candidate) < 8:
            continue

        if re.fullmatch(
            r"[\d\s,.]+\s*z[łl]",
            candidate,
            re.I,
        ):
            continue

        return candidate

    return ""


def reject_reason(row):
    """
    None = brak wykrytej sprzecznosci.
    Tekst = powod wykluczenia z rynku porownawczego.

    Nie usuwa ofert z bazy.
    """

    title = norm(field(row, "title"))
    gpu = norm(field(row, "gpu"))
    ram = field(row, "ram")

    if not gpu:
        return "MISSING_GPU"

    if is_placeholder_title(title):
        return "GENERIC_TITLE"

    # Intel Arc nie moze byc referencja cenowa RTX.
    # Wyceny Arc wymagaja osobnej obslugi GPU.
    if re.search(
        r"\b(?:INTEL\s+)?ARC\s+[AB]\s*-?\s*\d{3,4}\b",
        title,
    ):
        return "INTEL_ARC_REFERENCE"

    # Cena moze dotyczyc wersji bez dedykowanej GPU.
    if re.search(
        r"\bBEZ\s+(?:GPU|KARTY\s+GRAFICZNEJ)\b",
        title,
    ):
        return "PRICE_WITHOUT_GPU"

    # Rezerwacja na poczatku tytulu.
    if re.search(
        r"^\s*(?:REZERWACJA|ZAREZERWOWANY|"
        r"ZAREZERWOWANE|SPRZEDANY|SPRZEDANE)\b",
        title,
    ):
        return "RESERVED_OFFER"

    listed = gpu_models(title)
    saved = gpu_models(gpu)

    if saved and not listed:
        if re.search(
            r"\bVEGA\s*(?:3|6|7|8|10|11)\b",
            title,
        ):
            return "INTEGRATED_ONLY"

        if re.search(
            r"\bBAZA\s+POD\s+GAMING\b"
            r"|\bBEZ\s+KARTY\s+GRAFICZNEJ\b",
            title,
        ):
            return "NO_DEDICATED_GPU"

    if saved and re.search(
        r"\b(?:RX\s*)?VEGA\s*(?:56|64)\b",
        title,
    ):
        return "GPU_MISMATCH_VEGA"

    if len(listed) > 1:
        return "MULTI_GPU_TITLE"

    # Oferty wielowariantowe z GPU zapisana skrotem:
    # RX 7800 XT LUB 3080TI
    # RTX 3060 LUB 3060 Ti
    # 3080TI LUB RX 7800 XT
    if listed and re.search(
        r"\b(?:LUB|ALBO)\s+"
        r"(?:(?:RTX|GTX|RX)\s*-?\s*)?"
        r"(?:10[5678]0|16[56]0|20[678]0|"
        r"30[56789]0|40[56789]0|50[56789]0|"
        r"5[56789]\d{2}|6[56789]\d{2}|"
        r"7[56789]\d{2}|90[56789]0)"
        r"(?:\s*(?:TI|SUPER|XT|XTX|GRE))?\b",
        title,
    ):
        return "MULTI_GPU_TITLE"

    # Oferty wyraznie zawierajace monitor.
    optional_monitor = re.search(
        r"\b(?:OPCJA|BEZ|DOKUPIENIE)\s+MONITOR",
        title,
    )

    bundled_monitor = re.search(
        r"\bMONITOR(?:A|Y|AMI|EM|OW)?\b"
        r"|\bAOC\s+AGON\b",
        title,
    )

    if bundled_monitor and not optional_monitor:
        return "BUNDLE_MONITOR"

    # Zestawy podzespolow bez potwierdzenia calego PC.
    motherboard = re.search(
        r"\b(?:[ABHXZ]\s*-?\s*\d{3,4}|MORTAR|"
        r"PLYTA GLOWNA|MOTHERBOARD)\b",
        title,
    )

    complete_pc = re.search(
        r"\b(?:KOMPUTER|PC|DESKTOP)\b",
        title,
    )

    if (
        title.count("+") >= 2
        and motherboard
        and not complete_pc
        and not gpu_models(title)
    ):
        return "PARTS_BUNDLE"

    # GPU podana w tytule jest inna niz w bazie.
    listed_gpus = gpu_models(title)
    saved_gpus = gpu_models(gpu)

    if (
        listed_gpus
        and saved_gpus
        and listed_gpus.isdisjoint(saved_gpus)
    ):
        return "GPU_MISMATCH"

    # RAM jawnie podany w tytule jest inny niz w bazie.
    listed_ram = ram_values(title)

    try:
        saved_ram = int(ram)
    except (TypeError, ValueError):
        saved_ram = None

    if (
        len(listed_ram) == 1
        and saved_ram is not None
        and saved_ram not in listed_ram
    ):
        return "RAM_MISMATCH"

    return None
