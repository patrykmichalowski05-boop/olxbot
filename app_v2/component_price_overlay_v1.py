import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_CSV = Path(
    "/root/flip-pc-mvp/valuation-gui/catalog-stage/"
    "zatwierdzone_ceny_podzespolow.csv"
)

# Warianty wymagające dokładnego VRAM.
AMBIGUOUS_GPU = {
    "GTX 960", "GTX 1060",
    "RX 470", "RX 480",
    "RX 570", "RX 580",
    "RX 5500 XT",
}

# Modele wymagające wyjaśnienia nazwy.
REVIEW_CPU = {
    "RYZEN 7 5600G",
    "RYZEN 7 3700",
}


def provider(url):
    try:
        parsed = urlparse(str(url or "").strip())
        host = (parsed.hostname or "").lower()

        if parsed.scheme != "https":
            return None

        if not parsed.path or parsed.path == "/":
            return None

        for domain in (
            "olx.pl",
            "allegro.pl",
            "allegrolokalnie.pl",
            "facebook.com",
        ):
            if host == domain or host.endswith("." + domain):
                return domain

    except ValueError:
        pass

    return None


def load_approved(path=DEFAULT_CSV, apply=False):
    import valuation

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    required = {
        "typ", "model", "cena_zl",
        "zrodlo_1", "zrodlo_2", "zatwierdzono"
    }

    proposed = {"CPU": {}, "GPU": {}}
    errors = []

    with path.open(
        encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)

        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Brak wymaganych kolumn CSV")

        for line, row in enumerate(reader, 2):
            status = str(
                row.get("zatwierdzono") or ""
            ).strip().upper()

            if status != "TAK":
                continue

            kind = str(
                row.get("typ") or ""
            ).strip().upper()

            raw_model = str(
                row.get("model") or ""
            ).strip()

            if kind == "CPU":
                model = valuation.normalize_cpu(raw_model)
                table = valuation.CPU_VALUES
                maximum = 4000
            elif kind == "GPU":
                model = valuation.normalize_gpu(raw_model)
                table = valuation.GPU_VALUES
                maximum = 6000
            else:
                errors.append((line, "Nieznany typ"))
                continue

            if not model:
                errors.append((line, "Brak modelu"))
                continue

            if model in table:
                errors.append((
                    line, "Model już ma cenę w katalogu"
                ))
                continue

            if kind == "GPU" and model in AMBIGUOUS_GPU:
                errors.append((
                    line, "Niejednoznaczny wariant VRAM"
                ))
                continue

            if kind == "CPU" and model in REVIEW_CPU:
                errors.append((
                    line, "Model CPU wymaga potwierdzenia"
                ))
                continue

            try:
                amount = Decimal(
                    str(row.get("cena_zl") or "")
                    .replace(",", ".")
                    .strip()
                )
            except InvalidOperation:
                errors.append((line, "Niepoprawna cena"))
                continue

            if (
                not amount.is_finite()
                or amount != amount.to_integral_value()
                or not 10 <= amount <= maximum
            ):
                errors.append((line, "Cena poza zakresem"))
                continue

            p1 = provider(row.get("zrodlo_1"))
            p2 = provider(row.get("zrodlo_2"))

            if not p1 or not p2 or p1 == p2:
                errors.append((
                    line, "Wymagane dwa różne serwisy"
                ))
                continue

            if model in proposed[kind]:
                errors.append((line, "Zduplikowany model"))
                continue

            proposed[kind][model] = int(amount)

    if errors:
        for line, reason in errors[:20]:
            print("BLAD:", line, reason)

        raise ValueError(
            "Nieprawidłowe zatwierdzenia. "
            "Nie zmieniono żadnej ceny."
        )

    # Wszystkie dane są walidowane przed zmianą tabel.
    if apply:
        valuation.CPU_VALUES.update(proposed["CPU"])
        valuation.GPU_VALUES.update(proposed["GPU"])

    return proposed
