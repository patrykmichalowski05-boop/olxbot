from playwright.sync_api import Page
import re


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def meta_content(page, selector):
    try:
        loc = page.locator(selector)
        if loc.count():
            return clean_text(loc.first.get_attribute("content"))
    except:
        pass
    return ""


def extract_cpu(text):
    text = text.lower()

    # Ryzen 5 3600 / AMD Ryzen 5 5600X
    m = re.search(
        r"(?:amd\s+)?ryzen\s*([3579])\s*[- ]?\s*(\d{4}[a-z0-9]*)",
        text,
        re.I
    )

    if m:
        return f"Ryzen {m.group(1)} {m.group(2).upper()}"

    # r5 3600 / r5-5600x / R7 5700X
    m = re.search(
        r"\br\s*([3579])\s*[- ]?\s*(\d{4}[a-z0-9]*)\b",
        text,
        re.I
    )

    if m:
        return f"Ryzen {m.group(1)} {m.group(2).upper()}"

    # Intel Core i5-10400F / i5 10400f
    m = re.search(
        r"(?:intel\s+)?(?:core\s+)?i([3579])\s*[- ]?\s*(\d{4,5}[a-z]{0,2})\b",
        text,
        re.I
    )

    if m:
        return f"i{m.group(1)}-{m.group(2).upper()}"

    return None


def extract_gpu(text):
    """
    Rozpoznaje pierwsza GPU wedlug kolejnosci w tekscie,
    a nie wedlug producenta.
    """

    if not text:
        return None

    pattern = re.compile(
        r"\b(?:geforce\s+|radeon\s+)?"
        r"(RTX|GTX|RX)\s*-?\s*(\d{3,4})"
        r"(?:[\s-]*(XTX|SUPER|TI|XT|GRE))?\b",
        re.I,
    )

    match = pattern.search(str(text))

    if not match:
        return None

    vendor = match.group(1).upper()
    model = match.group(2)
    suffix = (match.group(3) or "").upper()

    result = f"{vendor} {model}"

    if suffix:
        result += f" {suffix}"

    return result



def extract_offer_gpu(title, ad_description, meta_description=""):
    """
    GPU z tytulu ma pierwszenstwo.

    Nie zgadujemy dedykowanej GPU, jesli tytul
    wskazuje baze bez karty lub samo iGPU.
    """
    title = str(title or "")

    title_gpu = extract_gpu(title)
    if title_gpu:
        return title_gpu

    no_dedicated_gpu = re.search(
        r"\bVEGA\s*(?:3|6|7|8|10|11)\b"
        r"|\bBAZA\s+POD\s+GAMING\b"
        r"|\bBEZ\s+KARTY\s+GRAFICZNEJ\b"
        r"|\bINTEL\s+UHD\b"
        r"|\bIRIS\s+XE\b",
        title,
        re.I,
    )

    if no_dedicated_gpu:
        return None

    return extract_gpu(
        ad_description or meta_description or ""
    )


def extract_disks(text):
    text = text.lower()

    disks = set()

    patterns = [
        r"\b(ssd|hdd|nvme|m\.2)\s*[:\-]?\s*(\d+)\s*(gb|tb)\b",
        r"\b(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|m\.2)\b"
    ]

    for match in re.finditer(patterns[0], text, re.I):
        disk_type = match.group(1).upper()
        size = match.group(2)
        unit = match.group(3).upper()

        disks.add(f"{disk_type} {size} {unit}")

    for match in re.finditer(patterns[1], text, re.I):
        size = match.group(1)
        unit = match.group(2).upper()
        disk_type = match.group(3).upper()

        disks.add(f"{disk_type} {size} {unit}")

    return sorted(disks)


def extract_offer(page: Page, url: str):

    print(f"\n[OTWIERAM] {url}")

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(2500)

    except Exception as e:
        print(f"[ERROR OPEN] {e}")
        return None

    # BODY
    try:
        body = page.locator("body").inner_text()
    except:
        body = ""

    # META
    og_title = meta_content(
        page,
        'meta[property="og:title"]'
    )

    description = meta_content(
        page,
        'meta[name="description"]'
    )

    # TYTUŁ
    title = None

    try:
        h1 = page.locator("h1")
        if h1.count():
            title = clean_text(h1.first.inner_text())
    except:
        pass

    if (
        not title
        or title.strip().casefold() in {
            "dostawa gratis",
            "darmowa dostawa",
            "wysyłka gratis",
            "odbiór osobisty",
        }
    ):
        title = og_title

    if title:
        # usuwa np. "Kętrzyn • OLX.pl"
        title = re.sub(
            r"\s+[^\s]+\s*[•|]\s*OLX\.pl.*$",
            "",
            title,
            flags=re.I
        )

        title = re.sub(
            r"\s*[•|]\s*OLX\.pl.*$",
            "",
            title,
            flags=re.I
        )

        title = clean_text(title)

    try:
        ad_description = clean_text(
            page.locator(
                '[data-cy="ad_description"]'
            ).first.inner_text(timeout=3000)
        )
    except Exception:
        ad_description = ""

    # Parametry wyłącznie z tytułu i opisu oferty.
    # Nie szukamy GPU/CPU/RAM w całym BODY OLX.
    specs_text = clean_text(
        f"{title or ''} {ad_description or description}"
    )
    specs_lower = specs_text.lower()

    # Zachowujemy dotychczasowe źródła
    # informacji o cenie i przesyłce.
    combined = clean_text(
        f"{title or ''} {description} {body}"
    )
    combined_lower = combined.lower()

    # CENA
    price = None

    prices = re.findall(
        r"(\d[\d\s]*(?:[,.]\d{2})?)\s*zł",
        combined,
        re.I
    )

    for value in prices:
        value = (
            value
            .replace(" ", "")
            .replace(",", ".")
        )

        try:
            number = int(float(value))

            if 100 <= number <= 50000:
                price = number
                break
        except:
            pass

    # RAM
    ram = None

    ram_patterns = [
        r"\b(\d{1,3})\s*gb\s*ram\b",
        r"\bram\s*[:\-]?\s*(\d{1,3})\s*gb\b",
        r"\b(\d{1,3})\s*gb\s*(?:ddr3|ddr4|ddr5)\b"
    ]

    for pattern in ram_patterns:
        match = re.search(pattern, specs_lower)

        if match:
            ram = int(match.group(1))
            break

    # PRZESYŁKA
    shipping_keywords = [
        "przesyłka olx",
        "kup z przesyłką",
        "pakiet ochronny",
        "przedmiot z pakietem ochronnym",
        "kup teraz"
    ]

    shipping = any(
        keyword in combined_lower
        for keyword in shipping_keywords
    )

    cpu = extract_cpu(specs_text)
    gpu = extract_offer_gpu(
        title,
        ad_description,
        description,
    )
    disks = extract_disks(specs_text)

    return {
        "title": title,
        "price": price,
        "cpu": cpu,
        "gpu": gpu,
        "ram": ram,
        "disks": disks,
        "shipping": shipping,
        "url": url
    }


def print_offer(data):

    print("\n" + "=" * 70)
    print("SZCZEGÓŁY OFERTY")

    print(f"Tytuł:     {data['title']}")
    print(f"Cena:      {data['price']} zł")
    print(f"CPU:       {data['cpu']}")
    print(f"GPU:       {data['gpu']}")
    print(f"RAM:       {data['ram']} GB")

    if data["disks"]:
        print("Dyski:     " + ", ".join(data["disks"]))
    else:
        print("Dyski:     brak danych")

    print(
        f"Przesyłka: "
        f"{'TAK' if data['shipping'] else 'NIE'}"
    )

    print(f"Link:      {data['url']}")
    print("=" * 70)
