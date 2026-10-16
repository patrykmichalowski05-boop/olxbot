import json
import math
import os
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

from app_v2.saved_searches_v1 import DB
from app_v2.seller_questions_preview_v1 import safe_url
from risk_flags_v1 import evaluate_risk

ROOT = Path("/root/flip-pc-mvp/valuation-gui")
PROD = Path("/opt/olx-bot")

SCANNER = ROOT / "pc_ranking_all_v1.py"
RANKING = ROOT / "pc_ranking_v1.json"
SNAPSHOT = PROD / "app_v2/pc_valuation_snapshot_v1.json"

PYTHON = PROD / "venv/bin/python"
PAGE = "/flip-radar/valuation-preview"

print("=== FLIP HUNTER - AUTO REFRESH ===", flush=True)

assert SCANNER.is_file()
assert SNAPSHOT.is_file()

# 1. Przelicz rynek osobnym procesem.
env = os.environ.copy()
env["PYTHONPATH"] = str(PROD)

result = subprocess.run(
    [str(PYTHON), str(SCANNER)],
    cwd=str(PROD),
    env=env,
    capture_output=True,
    text=True,
    timeout=300,
)

if result.returncode != 0:
    print(result.stdout[-4000:], flush=True)
    print(result.stderr[-4000:], flush=True)
    raise RuntimeError("Silnik wyceny zakonczyl sie bledem")

ranking = json.loads(
    RANKING.read_text(encoding="utf-8")
)

offers = ranking.get("offers")

assert isinstance(offers, list) and offers
assert len(offers) <= 5000
assert ranking.get("generated_utc")

print("PRZELICZONE:", len(offers), flush=True)

# 2. Pobierz aktualne ceny.
with sqlite3.connect(
    DB.resolve().as_uri() + "?mode=ro",
    uri=True
) as db:
    db.row_factory = sqlite3.Row
    current = {
        (str(r["source"]), str(r["listing_id"])):
            r["price_zl"]
        for r in db.execute("""
            SELECT source, listing_id, price_zl
            FROM offers
        """)
    }

def number(value):
    if type(value) not in (int, float):
        return None
    return value if math.isfinite(value) else None

rows = []
seen = set()
missing_from_db = 0

for offer in offers:
    assert offer.get("automation_allowed") is False

    identity = (
        str(offer.get("source")),
        str(offer.get("listing_id"))
    )

    if identity in seen:
        continue
    seen.add(identity)

    if identity not in current:
        missing_from_db += 1
        continue

    purchase = number(offer.get("purchase_zl"))
    resale = number(offer.get("estimated_resale_zl"))
    profit = number(offer.get("estimated_profit_zl"))

    if purchase is None or purchase <= 0:
        continue

    current_price = current[identity]
    changed = current_price != purchase

    if changed:
        group = "changed"
    elif profit is None:
        group = "unknown"
    elif profit >= 400:
        strong_market = (
            int(offer.get("exact_samples") or 0) >= 3
            and offer.get("confidence") in {
                "ŚREDNI", "WYSOKI", "BARDZO WYSOKI"
            }
        )
        group = "deal" if strong_market else "watch"
    else:
        group = "other"

    row = dict(offer)

    row.update({
        "url": safe_url(offer.get("url")),
        "price_zl": purchase,
        "resale_zl": resale,
        "profit_zl": profit,
        "ok": profit is not None,
        "current_price_zl": current_price,
        "price_changed": changed,
        "group": group,
        "profit_verified": False,
        "automation_allowed": False,
    })

    row.update(evaluate_risk(row))
    rows.append(row)

assert rows, "Brak wynikow do opublikowania"

priority = {
    "deal": 0,
    "watch": 1,
    "other": 2,
    "unknown": 3,
    "changed": 4,
}

rows.sort(
    key=lambda row: (
        priority[row["group"]],
        -(row["profit_zl"] or 0)
    )
)

snapshot = {
    "generated_utc": ranking["generated_utc"],
    "mode": "POLSKA",
    "profit_verified": False,
    "rows": rows,
}

# 3. Atomowy zapis z mozliwoscia przywrocenia.
previous = SNAPSHOT.read_bytes()
temporary = SNAPSHOT.with_name(
    SNAPSHOT.name + ".refresh.tmp"
)

try:
    temporary.write_text(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    os.chmod(temporary, 0o644)
    os.replace(temporary, SNAPSHOT)

    # 4. Test Flask na nowym rankingu.
    from app_v2 import create_app, config

    assert config.AUTH_REQUIRED is True

    app = create_app()
    app.testing = True

    with app.test_client() as client:
        guest = client.get(PAGE)
        assert guest.status_code in (
            301, 302, 303, 401, 403
        )

    app.before_request_funcs[None] = []

    with app.test_client() as client:
        response = client.get(PAGE)

        assert response.status_code == 200
        assert b"FLIP_RANKING_V1" in response.data
        assert response.data.count(
            b'class="offer-card"'
        ) == len(rows)

except Exception:
    temporary.write_bytes(previous)
    os.chmod(temporary, 0o644)
    os.replace(temporary, SNAPSHOT)
    print("PRZYWROCONO_POPRZEDNI_RANKING", flush=True)
    raise
finally:
    temporary.unlink(missing_ok=True)

counts = Counter(r["group"] for r in rows)

print("=== ODSWIEZENIE ZAKONCZONE ===", flush=True)
print("WSZYSTKIE:", len(rows))
print("SYGNALY_400_PLUS:", counts["deal"])
print("BEZ_WYCENY:", counts["unknown"])
print("PONIZEJ_400:", counts["other"])
print("ZMIANA_CENY:", counts["changed"])
print("NIEOBECNE_W_BAZIE:", missing_from_db)
print("AUTOMATYCZNE_WIADOMOSCI: WYLACZONE")
print("ODSWIEZENIE_OK", flush=True)
