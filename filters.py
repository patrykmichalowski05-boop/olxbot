import re

from scanner_settings import get_int


def cpu_ok(cpu):
    if not cpu:
        return False

    cpu = str(cpu).strip()

    # AMD Ryzen
    m = re.search(
        r"\bRyzen\s+([3579])\s+(\d{4})[A-Za-z0-9]*\b",
        cpu,
        re.I
    )

    if m:
        tier = int(m.group(1))
        model = int(m.group(2))

        # Minimum bazowe: Ryzen 5 3600.
        # Ryzen 7/9 również muszą być z rodziny 3000+
        # i nie mogą być starsze niż poziom 3600.
        if tier not in (5, 7, 9):
            return False

        return model >= 3600

    # Intel Core
    m = re.search(
        r"\bi([3579])-(\d{4,5})[A-Za-z0-9]*\b",
        cpu,
        re.I
    )

    if not m:
        return False

    tier = int(m.group(1))
    model = int(m.group(2))

    if tier == 5:
        # i5-9400/F lub nowszy
        if 9000 <= model < 10000:
            return model >= 9400

        return model >= 10000

    if tier == 7:
        # i7-8700 jest wystarczająco mocny względem i5-9400
        if 8000 <= model < 9000:
            return model >= 8700

        return model >= 9000

    if tier == 9:
        # i9 od 9 generacji
        return model >= 9000

    return False


def ram_ok(ram):
    if ram is None:
        return False

    try:
        return float(ram) >= get_int("min_ram_gb")
    except (TypeError, ValueError):
        return False


def purchase_price_ok(price):
    limit = get_int("max_purchase_price")

    # Zero oznacza brak limitu.
    if limit == 0:
        return True

    if price is None or isinstance(price, bool):
        return False

    try:
        amount = float(price)
    except (TypeError, ValueError):
        return False

    return 0 < amount <= limit


def hardware_ok(data):

    reasons = []

    cpu = data.get("cpu")
    ram = data.get("ram")

    # ========================================================
    # CPU
    # ========================================================

    if not cpu:
        reasons.append(
            "Brak informacji o CPU"
        )

    elif not cpu_ok(cpu):
        reasons.append(
            f"CPU nie spełnia minimum: {cpu}"
        )

    # ========================================================
    # RAM
    # ========================================================

    if ram is None:
        reasons.append(
            "Brak informacji o RAM"
        )

    elif not ram_ok(ram):
        reasons.append(
            f"RAM poniżej {get_int('min_ram_gb')} GB: {ram}"
        )

    return len(reasons) == 0, reasons

