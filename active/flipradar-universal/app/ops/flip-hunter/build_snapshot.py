import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from app_v2.saved_searches_v1 import DB
from app_v2.seller_questions_preview_v1 import safe_url
from valuation_v3 import estimate_flip_v3

OUT = Path(
    "/root/flip-pc-mvp/valuation-gui/snapshot.json"
)

with sqlite3.connect(
    DB.resolve().as_uri() + "?mode=ro",
    uri=True
) as db:
    db.row_factory = sqlite3.Row
    offers = [dict(r) for r in db.execute("""
        SELECT source, listing_id, title, url,
               price_zl, cpu, gpu, ram_gb, status
        FROM offers
        WHERE status='VERIFY_MARKET_AND_DELIVERY'
          AND cpu IS NOT NULL
          AND gpu IS NOT NULL
          AND ram_gb > 0
          AND price_zl BETWEEN 250 AND 5000
        ORDER BY last_seen_utc DESC
        LIMIT 12
    """)]

results = []

for offer in offers:
    details = {
        "price": offer["price_zl"],
        "cpu": offer["cpu"],
        "gpu": offer["gpu"],
        "ram": offer["ram_gb"],
    }

    try:
        valuation = estimate_flip_v3(details, "POLSKA")
        if not isinstance(valuation, dict):
            raise TypeError("Wycena nie zwrocila slownika")
    except Exception as exc:
        valuation = {
            "ok": False,
            "reason": str(exc)[:200],
        }

    row = {
        "source": offer["source"],
        "listing_id": offer["listing_id"],
        "title": offer["title"],
        "url": safe_url(offer["url"]),
        "cpu": offer["cpu"],
        "gpu": offer["gpu"],
        "ram_gb": offer["ram_gb"],
        "price_zl": offer["price_zl"],
        "ok": bool(valuation.get("ok")),
        "resale_zl": valuation.get("quick_sale"),
        "profit_zl": valuation.get("profit"),
        "confidence": valuation.get("confidence", "BRAK"),
        "valuation_source": valuation.get("valuation_source", "BRAK"),
        "exact_samples": valuation.get("exact_samples", 0),
        "reason": valuation.get("reason", ""),
        "status": "NIEZWERYFIKOWANA",
        "automation_allowed": False,
    }

    results.append(row)

    print(
        "PC:", offer["price_zl"], "zl |",
        offer["cpu"], "|", offer["gpu"],
        "| ODS:", row["resale_zl"],
        "| ZYSK:", row["profit_zl"],
        "| PEWNOSC:", row["confidence"],
        "| ZRODLO:", row["valuation_source"]
    )

snapshot = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "POLSKA",
    "rows": results,
}

OUT.write_text(
    json.dumps(snapshot, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\n=== KROK_42_OK ===")
print("PRZELICZONE:", len(results))
print("UDANE_WYCENY:", sum(r["ok"] for r in results))
print("SNAPSHOT:", OUT)
print("WIADOMOSCI_WYSLANE: 0")
