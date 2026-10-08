import importlib
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path("/opt/olx-bot")

ERRORS = []
WARNINGS = []


MODULES = [
    "scanner",
    "fast_scanner",
    "deep_worker",
    "priority_queue",
    "candidate_prefilter",
    "deal_action",
    "watchlist",
    "deal_crm",
    "crm_history",
    "crm_followup",
    "pickup_checklist",
    "sale_prep",
    "sale_pricing",
    "sale_listing_tracker",
    "listing_generator",
    "control_inventory",
    "dashboard",
]


DATABASES = {
    "fast.db": [],
    "market.db": [],
    "alert_history.db": [
        "alerts",
    ],
    "watchlist.db": [
        "watchlist",
    ],
    "deal_crm.db": [
        "deals",
        "followups",
        "deal_history",
        "pickup_checks",
        "sale_prep_costs",
        "sale_plans",
        "sale_listings",
    ],
    "flip_results.db": [
        "flips",
    ],
}


REQUIRED_ROUTE_PARTS = [
    "/control",
    "/health",
    "/offer/",
    "/history/add",
    "/followup/",
    "/pickup/check/",
    "/prep/cost",
    "/prep/plan",
    "/listed",
]


def ok(text):
    print(f"[ OK ] {text}")


def warn(text):
    WARNINGS.append(text)
    print(f"[WARN] {text}")


def error(text):
    ERRORS.append(text)
    print(f"[FAIL] {text}")


print()
print("========================================")
print(" OLX FLIP HUNTER - V1.0 PREFLIGHT")
print("========================================")
print()


# ============================================================
# 1. MODUŁY
# ============================================================

print("=== MODUŁY PYTHON ===")

for module in MODULES:
    try:
        importlib.import_module(module)
        ok(module)

    except Exception as exc:
        error(
            f"{module}: {type(exc).__name__}: {exc}"
        )


# ============================================================
# 2. SQLITE
# ============================================================

print()
print("=== BAZY SQLITE ===")

for filename, required_tables in DATABASES.items():

    path = ROOT / filename

    if not path.exists():
        warn(
            f"{filename} nie istnieje"
        )
        continue

    try:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
        )

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            error(
                f"{filename}: integrity_check={integrity}"
            )
        else:
            ok(
                f"{filename}: integrity OK"
            )

        tables = {
            row[0]
            for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
            """)
        }

        for table in required_tables:

            if table in tables:
                ok(
                    f"{filename}: tabela {table}"
                )
            else:
                error(
                    f"{filename}: BRAK tabeli {table}"
                )

        conn.close()

    except Exception as exc:
        error(
            f"{filename}: {exc}"
        )


# ============================================================
# 3. FLASK ROUTES
# ============================================================

print()
print("=== FLASK ROUTES ===")

try:
    from dashboard import app

    routes = sorted(
        str(rule)
        for rule in app.url_map.iter_rules()
    )

    for part in REQUIRED_ROUTE_PARTS:

        matching = [
            route
            for route in routes
            if part in route
        ]

        if matching:
            ok(
                f"{part} -> {matching[0]}"
            )
        else:
            error(
                f"brak route zawierającego {part}"
            )

except Exception as exc:
    error(
        f"Flask route map: {exc}"
    )


# ============================================================
# 4. DASHBOARD HTTP
# ============================================================

print()
print("=== HTTP ===")

for url in [
    "http://127.0.0.1:8088/control",
    "http://127.0.0.1:8088/health",
]:

    try:
        response = urllib.request.urlopen(
            url,
            timeout=5,
        )

        code = response.getcode()

        if code == 200:
            ok(
                f"{url} -> 200"
            )
        else:
            error(
                f"{url} -> {code}"
            )

    except Exception as exc:
        error(
            f"{url}: {exc}"
        )


# ============================================================
# 5. TIMERY
# ============================================================

print()
print("=== SYSTEMD ===")

timers = [
    "olx-fast.timer",
    "olx-deep.timer",
    "olx-bundle.timer",
    "olx-market.timer",
    "olx-watchdog.timer",
    "olx-near-miss.timer",
    "olx-lifecycle.timer",
    "olx-watchlist-lifecycle.timer",
    "olx-daily-report.timer",
    "olx-followup.timer",
    "olx-sale-monitor.timer",
    "olx-backup.timer",
]


for timer in timers:

    result = subprocess.run(
        [
            "systemctl",
            "is-active",
            timer,
        ],
        capture_output=True,
        text=True,
    )

    state = result.stdout.strip()

    if state == "active":
        ok(
            f"{timer}: active"
        )

    else:
        warn(
            f"{timer}: {state or 'unknown'}"
        )


# ============================================================
# PODSUMOWANIE
# ============================================================

print()
print("========================================")

if ERRORS:

    print(
        f"PREFLIGHT FAILED: {len(ERRORS)} błędów"
    )

    for item in ERRORS:
        print(
            " -",
            item,
        )

    print("========================================")

    sys.exit(1)


print("V1.0 PREFLIGHT OK")

print(
    f"Ostrzeżenia: {len(WARNINGS)}"
)

for item in WARNINGS:
    print(
        " -",
        item,
    )

print("========================================")

sys.exit(0)
