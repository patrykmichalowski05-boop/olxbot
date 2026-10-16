import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import valuation
from valuation_v3 import estimate_flip_v3
from app_v2.saved_searches_v1 import DB

ROOT = Path("/root/flip-pc-mvp/valuation-gui")
STAGE = ROOT / "catalog-stage"
STAGE.mkdir(parents=True, exist_ok=True)

SNAPSHOT = Path(
    "/opt/olx-bot/app_v2/pc_valuation_snapshot_v1.json"
)

rows = json.loads(
    SNAPSHOT.read_text(encoding="utf-8")
)["rows"]

unknown = [
    r for r in rows
    if r.get("group") == "unknown"
]

assert unknown
assert all(
    r.get("automation_allowed") is False
    for r in unknown
)

# ==========================================
# KROK 66 - BRAKI KATALOGU
# ==========================================

print("\n=== KROK_66: BRAKI KATALOGU ===")

missing = defaultdict(list)

for r in unknown:
    cpu = valuation.normalize_cpu(r.get("cpu"))
    gpu = valuation.normalize_gpu(r.get("gpu"))

    if cpu not in valuation.CPU_VALUES:
        missing[("CPU", cpu)].append(r)

    if gpu not in valuation.GPU_VALUES:
        missing[("GPU", gpu)].append(r)

print("BRAK_WYCENY_PC:", len(unknown))
print("BRAKUJACE_MODELE:", len(missing))
print("CPU:", sum(k == "CPU" for k, _ in missing))
print("GPU:", sum(k == "GPU" for k, _ in missing))

# ==========================================
# KROK 67 - MATERIAŁ DO WERYFIKACJI
# ==========================================

print("\n=== KROK_67: DANE Z ISTNIEJACYCH OFERT ===")

with sqlite3.connect(
    DB.resolve().as_uri() + "?mode=ro",
    uri=True
) as db:
    db.row_factory = sqlite3.Row

    offers = [
        dict(r) for r in db.execute("""
            SELECT source, listing_id, title,
                   url, price_zl, cpu, gpu
            FROM offers
            WHERE price_zl > 0
        """)
    ]

    assert db.execute(
        "PRAGMA quick_check"
    ).fetchone()[0] == "ok"


def safe_link(value):
    try:
        p = urlparse(str(value or ""))
        host = (p.hostname or "").lower()

        allowed = (
            "olx.pl",
            "facebook.com",
            "allegro.pl",
            "allegrolokalnie.pl",
        )

        if p.scheme == "https" and any(
            host == domain
            or host.endswith("." + domain)
            for domain in allowed
        ):
            return p.geturl()

    except ValueError:
        pass

    return ""


evidence = defaultdict(list)

for r in offers:
    for kind, model in (
        ("CPU", valuation.normalize_cpu(r["cpu"])),
        ("GPU", valuation.normalize_gpu(r["gpu"])),
    ):
        key = (kind, model)
        url = safe_link(r["url"])

        if key not in missing or not url:
            continue

        if (
            url not in evidence[key]
            and len(evidence[key]) < 3
        ):
            evidence[key].append(url)

research = STAGE / "brakujace_modele_z_przykladami_pc.csv"

with research.open(
    "w", encoding="utf-8-sig", newline=""
) as f:
    writer = csv.writer(f)

    writer.writerow([
        "typ",
        "model",
        "liczba_niewycenionych_pc",
        "przyklad_pc_1",
        "przyklad_pc_2",
        "przyklad_pc_3",
        "uwaga",
    ])

    for key, related in sorted(
        missing.items(),
        key=lambda x: (-len(x[1]), x[0])
    ):
        urls = (evidence[key] + ["", "", ""])[:3]

        writer.writerow([
            key[0],
            key[1],
            len(related),
            *urls,
            "Linki dotycza CALYCH komputerow, "
            "nie cen samych podzespolow",
        ])

print("RAPORT:", research)

# ==========================================
# KROK 68 - KATALOG DO ZATWIERDZENIA
# ==========================================

print("\n=== KROK_68: KATALOG ZATWIERDZANIA ===")

approval = STAGE / "zatwierdzone_ceny_podzespolow.csv"

if not approval.exists():
    with approval.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.writer(f)

        writer.writerow([
            "typ",
            "model",
            "cena_zl",
            "zrodlo_1",
            "zrodlo_2",
            "zatwierdzono",
        ])

        for kind, model in sorted(missing):
            writer.writerow([
                kind, model, "", "", "", "NIE"
            ])

    print("UTWORZONO:", approval)

else:
    print("ISTNIEJACY_PLIK_ZACHOWANY:", approval)

# ==========================================
# KROK 69 - WALIDACJA NOWYCH CEN
# ==========================================

print("\n=== KROK_69: WALIDACJA ZATWIERDZEN ===")

approved = []
errors = []

with approval.open(
    encoding="utf-8-sig", newline=""
) as f:
    for line, r in enumerate(csv.DictReader(f), 2):
        if (
            r.get("zatwierdzono") or ""
        ).strip().upper() != "TAK":
            continue

        kind = (r.get("typ") or "").strip().upper()
        model = (r.get("model") or "").strip().upper()
        key = (kind, model)

        try:
            price = float(
                (r.get("cena_zl") or "")
                .replace(",", ".")
                .strip()
            )
        except (ValueError, TypeError):
            errors.append((line, "Nieprawidlowa cena"))
            continue

        limit = 4000 if kind == "CPU" else 6000

        sources = [
            safe_link(r.get(k))
            for k in ("zrodlo_1", "zrodlo_2")
        ]

        current = (
            valuation.CPU_VALUES
            if kind == "CPU"
            else valuation.GPU_VALUES
        )

        if (
            kind not in ("CPU", "GPU")
            or key not in missing
            or model in current
        ):
            errors.append((line, "Model nie jest brakiem"))

        elif (
            not math.isfinite(price)
            or not 10 <= price <= limit
        ):
            errors.append((line, "Cena poza zakresem"))

        elif (
            not all(sources)
            or len(set(sources)) < 2
        ):
            errors.append((
                line,
                "Wymagane dwa rozne linki HTTPS"
            ))

        else:
            approved.append((
                kind, model, round(price)
            ))

if errors:
    for line, reason in errors[:20]:
        print("BLAD_WIERSZA:", line, reason)

    raise RuntimeError(
        "Niepoprawne zatwierdzenia - "
        "nie wprowadzono zmian"
    )

assert len({
    (kind, model)
    for kind, model, price in approved
}) == len(approved), "Duplikaty zatwierdzen"

print("ZATWIERDZONE_MODELE:", len(approved))

# ==========================================
# KROK 70 - SYMULACJA, BEZ ZAPISU DO PROD
# ==========================================

print("\n=== KROK_70: SYMULACJA WYCEN ===")

old_cpu = valuation.CPU_VALUES.copy()
old_gpu = valuation.GPU_VALUES.copy()

try:
    for kind, model, price in approved:
        table = (
            valuation.CPU_VALUES
            if kind == "CPU"
            else valuation.GPU_VALUES
        )

        table[model] = price

    changed = []

    for row in unknown:
        details = {
            "price": row.get("purchase_zl"),
            "cpu": row.get("cpu"),
            "gpu": row.get("gpu"),
            "ram": row.get("ram_gb"),
        }

        static = valuation.static_valuation(details)

        if static.get("ok"):
            estimated = estimate_flip_v3(
                details, "POLSKA"
            )
            changed.append((row, estimated))

    print("NOWE_WYCENY_STATIC:", len(changed))

    changed.sort(
        key=lambda item: (
            -(item[1].get("profit") or -999999)
        )
    )

    for row, result in changed[:12]:
        print(
            "SYMULACJA:",
            row.get("purchase_zl"), "zl |",
            row.get("cpu"), "|",
            row.get("gpu"), "|",
            "ZYSK:", result.get("profit"), "|",
            "PEWNOSC:", result.get("confidence")
        )

finally:
    valuation.CPU_VALUES.clear()
    valuation.CPU_VALUES.update(old_cpu)

    valuation.GPU_VALUES.clear()
    valuation.GPU_VALUES.update(old_gpu)

print("\n=== KROKI_66_70_OK ===")
print("BAZA: BEZ ZMIAN")
print("GUI: BEZ ZMIAN")
print("TIMERY: BEZ ZMIAN")
print("CENNIK_PRODUKCYJNY: BEZ ZMIAN")
print("WIADOMOSCI_AUTOMATYCZNE: WYLACZONE")
