import csv
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import valuation
from valuation_v3 import estimate_flip_v3

ROOT = Path("/root/flip-pc-mvp/valuation-gui/catalog-stage")
SNAPSHOT = Path(
    "/opt/olx-bot/app_v2/pc_valuation_snapshot_v1.json"
)

# CENY ROBOCZE - NIEZATWIERDZONE
# To obserwacje ofertowe, nie ceny transakcyjne.

RESEARCH = {
    "I5-7400": {
        "price": 55,
        "sources": [
            (
                50,
                "https://www.olx.pl/d/oferta/"
                "intel-core-i5-7400-CID99-ID17ASRI.html"
            ),
            (
                55,
                "https://allegrolokalnie.pl/oferta/"
                "procesor-intel-core-i57400-pw6"
            ),
        ],
    },
    "RYZEN 7 2700": {
        "price": 180,
        "sources": [
            (
                169,
                "https://www.olx.pl/d/oferta/"
                "procesor-amd-ryzen-7-2700-CID99-ID1cifpe.html"
            ),
            (
                180,
                "https://www.olx.pl/d/oferta/"
                "ryzen-7-2700-8rdzeni-CID99-ID1bGtlW.html"
            ),
            (
                229.99,
                "https://allegro.pl/oferta/"
                "procesor-amd-ryzen-7-2700-8x3-2ghz-16mb-am4-"
                "18481925475"
            ),
        ],
    },
    "RYZEN 7 2700X": {
        "price": 200,
        "sources": [
            (
                200,
                "https://www.olx.pl/d/oferta/"
                "amd-ryzen-7-2700x-3-7ghz-CID99-ID1bWvQb.html"
            ),
            (
                199,
                "https://allegrolokalnie.pl/oferta/"
                "amd-ryzem-7-2700-x"
            ),
        ],
    },
}


def provider(url):
    host = (urlparse(url).hostname or "").lower()

    if host.endswith("olx.pl"):
        return "OLX"
    if host.endswith("allegrolokalnie.pl"):
        return "ALLEGRO_LOKALNIE"
    if host.endswith("allegro.pl"):
        return "ALLEGRO"

    raise ValueError("Nieznane zrodlo: " + url)


def safe_csv(value):
    text = str(value if value is not None else "")
    return "'" + text if text.startswith(
        ("=", "+", "-", "@")
    ) else text


def write_csv(path, fields, rows):
    with path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


# ============================================
# 91 - STAN PRZED SYMULACJA
# ============================================

print("=== KROK_91: STAN WYJSCIOWY ===")

snapshot = json.loads(
    SNAPSHOT.read_text(encoding="utf-8")
)

unknown = [
    r for r in snapshot["rows"]
    if r.get("group") == "unknown"
]

cpu_before = valuation.CPU_VALUES.copy()
gpu_before = valuation.GPU_VALUES.copy()

assert unknown
assert all(
    r.get("automation_allowed") is False
    for r in unknown
)

for model in RESEARCH:
    assert model not in cpu_before

print("PC_BEZ_WYCENY:", len(unknown))
print("NOWE_MODELE_DO_SYMULACJI:", len(RESEARCH))
print("KROK_91_OK")


# ============================================
# 92 - KONTROLA ZRODEL I CEN
# ============================================

print("\n=== KROK_92: MATERIAL RYNKOWY ===")

evidence_rows = []

for model, data in RESEARCH.items():
    price = data["price"]
    sources = data["sources"]

    assert 10 <= price <= 4000
    assert len(sources) >= 2

    providers = {provider(url) for _, url in sources}

    assert "OLX" in providers
    assert (
        "ALLEGRO" in providers
        or "ALLEGRO_LOKALNIE" in providers
    )

    for asking, url in sources:
        assert math.isfinite(asking)
        assert asking > 0
        assert urlparse(url).scheme == "https"

        evidence_rows.append({
            "typ": "CPU",
            "model": model,
            "cena_testowa_zl": price,
            "cena_ogloszenia_zl": asking,
            "serwis": provider(url),
            "link": url,
            "status": "CENA_OFERTOWA_DO_SPRAWDZENIA",
        })

evidence_path = ROOT / "research_3cpu_sources.csv"

write_csv(
    evidence_path,
    [
        "typ", "model", "cena_testowa_zl",
        "cena_ogloszenia_zl", "serwis",
        "link", "status"
    ],
    evidence_rows
)

print("OFERTY_ZRODLOWE:", len(evidence_rows))
print("RAPORT:", evidence_path)
print("KROK_92_OK")


# ============================================
# 93 - PRZYGOTOWANIE WERSJI DO AKCEPTACJI
# ============================================

print("\n=== KROK_93: PROPOZYCJE CEN ===")

proposal_rows = []

for model, data in RESEARCH.items():
    urls = [url for _, url in data["sources"]]

    olx = next(
        u for u in urls if provider(u) == "OLX"
    )

    other = next(
        u for u in urls
        if provider(u) != "OLX"
    )

    proposal_rows.append({
        "typ": "CPU",
        "model": model,
        "cena_zl": data["price"],
        "zrodlo_1": olx,
        "zrodlo_2": other,
        "zatwierdzono": "NIE",
    })

proposal_path = ROOT / "propozycje_3cpu_NIEZATWIERDZONE.csv"

write_csv(
    proposal_path,
    [
        "typ", "model", "cena_zl",
        "zrodlo_1", "zrodlo_2", "zatwierdzono"
    ],
    proposal_rows
)

print("MODELE:", len(proposal_rows))
print("ZATWIERDZONE: 0")
print("PLIK:", proposal_path)
print("KROK_93_OK")


# ============================================
# 94 - SYMULACJA NA SILNIKU V3
# ============================================

print("\n=== KROK_94: SYMULACJA V3 ===")

simulation = []

try:
    valuation.CPU_VALUES.update({
        model: info["price"]
        for model, info in RESEARCH.items()
    })

    for offer in unknown:
        cpu = valuation.normalize_cpu(
            offer.get("cpu")
        )

        if cpu not in RESEARCH:
            continue

        details = {
            "price": offer.get("purchase_zl"),
            "cpu": offer.get("cpu"),
            "gpu": offer.get("gpu"),
            "ram": offer.get("ram_gb"),
        }

        base_gpu_known = (
            valuation.normalize_gpu(
                offer.get("gpu")
            ) in valuation.GPU_VALUES
        )

        try:
            static = valuation.static_valuation(details)

            result = (
                estimate_flip_v3(details, "POLSKA")
                if static.get("ok")
                else {
                    "ok": False,
                    "reason": static.get("reason"),
                }
            )

        except Exception as exc:
            result = {
                "ok": False,
                "reason": str(exc)[:160],
            }

        profit = result.get("profit")

        simulation.append({
            "cpu": cpu,
            "gpu": offer.get("gpu"),
            "ram_gb": offer.get("ram_gb"),
            "cena_pc_zl": offer.get("purchase_zl"),
            "cpu_test_zl": RESEARCH[cpu]["price"],
            "gpu_ma_cene": base_gpu_known,
            "wycena_ok": bool(result.get("ok")),
            "odsprzedaz_model_zl": result.get(
                "quick_sale"
            ),
            "wynik_modelu_zl": profit,
            "zrodlo_wyceny": result.get(
                "valuation_source"
            ),
            "pewnosc": result.get("confidence"),
            "powod": result.get("reason", ""),
            "tytul": safe_csv(offer.get("title")),
            "url": offer.get("url") or "",
            "status": "TYLKO_SYMULACJA_NIE_KUPUJ",
        })

finally:
    valuation.CPU_VALUES.clear()
    valuation.CPU_VALUES.update(cpu_before)

    valuation.GPU_VALUES.clear()
    valuation.GPU_VALUES.update(gpu_before)

assert valuation.CPU_VALUES == cpu_before
assert valuation.GPU_VALUES == gpu_before

simulation_path = ROOT / "symulacja_3cpu_v3.csv"

write_csv(
    simulation_path,
    [
        "cpu", "gpu", "ram_gb",
        "cena_pc_zl", "cpu_test_zl",
        "gpu_ma_cene", "wycena_ok",
        "odsprzedaz_model_zl", "wynik_modelu_zl",
        "zrodlo_wyceny", "pewnosc",
        "powod", "tytul", "url", "status"
    ],
    simulation
)

print("DOTKNIETE_PC:", len(simulation))
print(
    "NOWE_WYCENY_V3:",
    sum(r["wycena_ok"] for r in simulation)
)

print(
    "NAD_PROGIEM_400_TYLKO_TEST:",
    sum(
        r["wycena_ok"]
        and isinstance(
            r["wynik_modelu_zl"], (int, float)
        )
        and r["wynik_modelu_zl"] >= 400
        for r in simulation
    )
)

print("KROK_94_OK")


# ============================================
# 95 - RAPORT KONCOWY
# ============================================

print("\n=== KROK_95: KONTROLA I RAPORT ===")

assert valuation.CPU_VALUES == cpu_before
assert valuation.GPU_VALUES == gpu_before

for item in simulation:
    print(
        "CPU:", item["cpu"],
        "| GPU:", item["gpu"],
        "| zakup:", item["cena_pc_zl"],
        "| wynik:", item["wynik_modelu_zl"],
        "| źródło:", item["zrodlo_wyceny"]
    )

print("\nZRODLA_CEN:", evidence_path)
print("PROPOZYCJE:", proposal_path)
print("SYMULACJA:", simulation_path)

print("BAZA: BEZ ZMIAN")
print("VALUATION_PY: BEZ ZMIAN")
print("ZATWIERDZENIA: BEZ ZMIAN")
print("GUI: BEZ ZMIAN")
print("TIMERY: BEZ ZMIAN")
print("=== KROKI_91_95_OK ===")
