import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app_v2.saved_searches_v1 import DB
from app_v2.spec_enrichment_v1 import extract
from valuation_v3 import estimate_flip_v3

ROOT = Path("/root/flip-pc-mvp/valuation-gui")
ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_STATUSES = (
    "VERIFY_MARKET_AND_DELIVERY",
    "REVIEW_SPECS",
    "REVIEW_CPU_PERFORMANCE",
)

RAM_VALUES = {4, 8, 12, 16, 24, 32, 48, 64, 96, 128}
PRICE_BUCKETS = (
    (250, 999),
    (1000, 1499),
    (1500, 1999),
    (2000, 2999),
    (3000, 5000),
)

now = datetime.now(timezone.utc)

print("=== 46/50: ODCZYT OFERT ===", flush=True)

with sqlite3.connect(
    DB.resolve().as_uri() + "?mode=ro",
    uri=True
) as db:
    db.row_factory = sqlite3.Row

    raw = [
        dict(row) for row in db.execute("""
            SELECT source, listing_id, title, url,
                   price_zl, cpu, gpu, ram_gb,
                   status, last_seen_utc
            FROM offers
            WHERE status IN (?, ?, ?)
              AND price_zl BETWEEN 250 AND 5000
              AND cpu IS NOT NULL
              AND gpu IS NOT NULL
              AND ram_gb > 0
        """, ALLOWED_STATUSES)
    ]

print("OFERTY_WEJSCIOWE:", len(raw))

print("\n=== 47/50: WALIDACJA PARAMETROW ===", flush=True)

rejections = Counter()
eligible = []

def norm(value):
    return re.sub(r"\s+", "", str(value or "")).upper()

def is_recent(value):
    try:
        dt = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        days = (now - dt).total_seconds() / 86400
        return 0 <= days <= 45
    except (ValueError, TypeError):
        return False

for offer in raw:
    title = str(offer["title"] or "")

    if not is_recent(offer["last_seen_utc"]):
        rejections["STARE_LUB_BEZ_DATY"] += 1
        continue

    if re.search(
        r"\b(laptop|notebook|uszkodz\w*|"
        r"niesprawn\w*|zamieni\w*)\b",
        title, re.I
    ):
        rejections["NIEODPOWIEDNI_STAN_LUB_TYP"] += 1
        continue

    if re.search(
        r"\b(?:2|3|4)\s*[x×]\s*(?:RTX|GTX|RX)\b",
        title, re.I
    ):
        rejections["WIELE_KART_GPU"] += 1
        continue

    try:
        ram = int(offer["ram_gb"])
    except (ValueError, TypeError):
        ram = 0

    if ram not in RAM_VALUES:
        rejections["NIEPRAWIDLOWY_RAM"] += 1
        continue

    parsed = extract(title)

    gpu_title = parsed.get("gpu")
    if gpu_title and norm(gpu_title) != norm(offer["gpu"]):
        rejections["KONFLIKT_GPU"] += 1
        continue

    cpu_title = parsed.get("cpu")
    if cpu_title and norm(cpu_title) != norm(offer["cpu"]):
        rejections["KONFLIKT_CPU"] += 1
        continue

    ram_title = parsed.get("ram_gb")
    if ram_title and ram_title != ram:
        rejections["KONFLIKT_RAM"] += 1
        continue

    eligible.append(offer)

print("PO_WALIDACJI:", len(eligible))
print("ODRZUCONE:", dict(rejections))

print("\n=== 48/50: WYBOR Z ROZNYCH CEN ===", flush=True)

selected = []
seen = set()

for low, high in PRICE_BUCKETS:
    group = sorted(
        [
            offer for offer in eligible
            if low <= offer["price_zl"] <= high
        ],
        key=lambda item: (
            item["price_zl"],
            str(item["listing_id"])
        )
    )

    count = 0

    for offer in group:
        identity = (
            str(offer["source"]),
            str(offer["listing_id"])
        )

        if identity in seen:
            continue

        selected.append(offer)
        seen.add(identity)
        count += 1

        if count >= 25:
            break

    print(f"{low}-{high} zl: {count} ofert")

print("DO_WYCENY:", len(selected))

print("\n=== 49/50: SILNIK VALUATION V3 ===", flush=True)

results = []

for index, offer in enumerate(selected, 1):
    details = {
        "price": int(offer["price_zl"]),
        "cpu": offer["cpu"],
        "gpu": offer["gpu"],
        "ram": int(offer["ram_gb"]),
    }

    try:
        valuation = estimate_flip_v3(details, "POLSKA")
        if not isinstance(valuation, dict):
            raise TypeError("Nieprawidlowy wynik wyceny")
    except Exception as error:
        valuation = {
            "ok": False,
            "reason": str(error)[:200],
        }

    ok = bool(valuation.get("ok"))

    resale = valuation.get("quick_sale") if ok else None
    profit = valuation.get("profit") if ok else None

    if ok and (
        not isinstance(resale, (int, float))
        or not isinstance(profit, (int, float))
    ):
        ok = False
        resale = None
        profit = None

    if not ok:
        signal = "BRAK_WYCENY"
    elif profit >= 700:
        signal = "SYGNAL_700_NIEZWERYFIKOWANY"
    elif profit >= 400:
        signal = "SYGNAL_400_NIEZWERYFIKOWANY"
    else:
        signal = "PONIZEJ_400"

    # Dane ofertowe i dostawa nie sa zweryfikowane.
    # Nie wolno automatycznie akceptowac zakupu.
    item = {
        "source": offer["source"],
        "listing_id": offer["listing_id"],
        "title": offer["title"],
        "url": offer["url"],
        "original_status": offer["status"],
        "cpu": offer["cpu"],
        "gpu": offer["gpu"],
        "ram_gb": offer["ram_gb"],
        "purchase_zl": offer["price_zl"],
        "estimated_resale_zl": resale,
        "estimated_profit_zl": profit,
        "confidence": valuation.get("confidence", "BRAK"),
        "valuation_source": valuation.get(
            "valuation_source", "BRAK"
        ),
        "exact_samples": valuation.get("exact_samples", 0),
        "reason": valuation.get("reason", ""),
        "signal": signal,
        "shipping_verified": False,
        "profit_verified": False,
        "automation_allowed": False,
    }

    results.append(item)

    if index % 25 == 0 or index == len(selected):
        print(
            f"PRZELICZONO: {index}/{len(selected)}",
            flush=True
        )

print("\n=== 50/50: RANKING I RAPORT ===", flush=True)

results.sort(
    key=lambda r: (
        r["estimated_profit_zl"] is None,
        -(r["estimated_profit_zl"] or 0)
    )
)

csv_path = ROOT / "pc_ranking_v1.csv"
json_path = ROOT / "pc_ranking_v1.json"

if results:
    tmp_csv = csv_path.with_suffix(".csv.tmp")

    with tmp_csv.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=list(results[0])
        )
        writer.writeheader()
        writer.writerows(results)

    tmp_csv.replace(csv_path)

snapshot = {
    "generated_utc": now.isoformat(),
    "mode": "POLSKA",
    "profit_verified": False,
    "offers": results,
}

tmp_json = json_path.with_suffix(".json.tmp")
tmp_json.write_text(
    json.dumps(snapshot, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
tmp_json.replace(json_path)

summary = Counter(r["signal"] for r in results)

print("STATUSY:", dict(summary))

print("\n=== TOP 20 WYNIKOW ===")

for r in results[:20]:
    print(
        r["signal"],
        "| zakup:", r["purchase_zl"],
        "| odsprzedaz:", r["estimated_resale_zl"],
        "| wynik:", r["estimated_profit_zl"],
        "|", r["cpu"],
        "|", r["gpu"],
        "| pewnosc:", r["confidence"],
        "|", r["valuation_source"]
    )

print("\nCSV:", csv_path if results else "Brak wynikow")
print("JSON:", json_path)
print("=== KROK_50_OK ===")
print("PRODUKCJA: BEZ ZMIAN")
print("AUTOMATYCZNE_WIADOMOSCI: WYLACZONE")
