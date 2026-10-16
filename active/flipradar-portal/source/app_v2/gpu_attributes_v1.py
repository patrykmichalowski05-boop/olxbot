import re
import unicodedata


BRANDS = (
    "asus", "msi", "gigabyte", "palit",
    "gainward", "zotac", "inno3d", "pny"
)

SERIES = (
    "gaming x", "windforce", "infinity",
    "ventus", "prime", "strix", "tuf",
    "ghost", "eagle", "dual", "gaming"
)


def normalize(value):
    value = str(value or "").lower()
    value = value.replace("ł", "l")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", value).strip()


def has(text, pattern):
    return bool(re.search(pattern, text))


def analyze(title):
    s = normalize(title)

    model = "nieustalony"

    if has(s, r"\brtx[\s-]*5060[\s-]*ti\b"):
        model = "RTX 5060 Ti"
    elif has(s, r"\brtx[\s-]*5060\b"):
        model = "RTX 5060"

    vram = None
    match = re.search(r"\b(8|16)\s*gb\b", s)

    if match:
        vram = int(match.group(1))

    brand = "nieustalony"

    for name in BRANDS:
        if has(s, rf"\b{re.escape(name)}\b"):
            brand = name.upper()
            break

    series = "nieustalona"

    for name in SERIES:
        if has(s, rf"\b{re.escape(name)}\b"):
            series = name.upper()
            break

    used = has(
        s,
        r"\buzywan[ayoe]\b|\bstan uzywany\b"
    )

    new = has(
        s,
        r"\bnow[ay]\b|\bfabrycznie now[ay]\b"
        r"|\bnieuzywan[ay]\b|\bnieotwieran[ay]\b"
    )

    if has(s, r"\b(jak|prawie)\s+now[ay]\b"):
        new = False

    if new and not used:
        condition = "nowy_deklarowany"
    elif used and not new:
        condition = "uzywany_deklarowany"
    else:
        condition = "nieustalony"

    if has(
        s,
        r"\b(bez|brak|po)\s+gwarancji\b"
    ):
        warranty = "brak_deklarowany"
    elif has(s, r"\bgwarancj|\bgwar\b"):
        warranty = "deklarowana"
    else:
        warranty = "nieustalona"

    proof = has(
        s,
        r"\bparagon\b|\bfaktur[ay]\b"
        r"|\bdowod zakupu\b"
    )

    return {
        "model": model,
        "vram_gb": vram,
        "brand": brand,
        "series": series,
        "condition": condition,
        "warranty": warranty,
        "proof_declared": proof,
        "source": "tytul_ogloszenia"
    }
