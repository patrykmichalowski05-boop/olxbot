import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOT_ROOT = Path(os.getenv("OLX_BOT_DIR", str(PROJECT_ROOT))).resolve()

DATABASES = {
    "fast": BOT_ROOT / "fast.db",
    "market": BOT_ROOT / "market.db",
    "alerts": BOT_ROOT / "alert_history.db",
    "flips": BOT_ROOT / "flip_results.db",
    "crm": BOT_ROOT / "deal_crm.db",
    "watchlist": BOT_ROOT / "watchlist.db",
    "snapshots": BOT_ROOT / "offer_snapshots.db",
    "checks": BOT_ROOT / "purchase_checklist.db",
    "decisions": BOT_ROOT / "decision_log.db",
    "facebook": BOT_ROOT / "facebook" / "facebook_seen.db",
}

CRM_STATUSES = (
    "NEW",
    "CONTACTED",
    "NEGOTIATING",
    "PICKUP",
    "BOUGHT",
    "PREPARING",
    "READY_TO_SELL",
    "LISTED",
    "SOLD",
    "SKIPPED",
)

CRM_LABELS = {
    "NEW": "Nowe",
    "CONTACTED": "Kontakt",
    "NEGOTIATING": "Negocjacja",
    "PICKUP": "Odbiór",
    "BOUGHT": "Kupione",
    "PREPARING": "Przygotowanie",
    "READY_TO_SELL": "Gotowe do sprzedaży",
    "LISTED": "Wystawione",
    "SOLD": "Sprzedane",
    "SKIPPED": "Odrzucone",
}

# Jedyna lista usług, które GUI może uruchamiać. Żaden parametr
# przesłany z przeglądarki nie trafia bezpośrednio do systemctl.
JOBS = {
    "fast": {"label": "FAST Radar", "service": "olx-fast.service"},
    "deep": {"label": "DEEP Worker", "service": "olx-deep.service"},
    "bundle": {"label": "Bundle Radar", "service": "olx-bundle.service"},
    "market": {"label": "Market Collector", "service": "olx-market.service"},
    "lifecycle": {"label": "Market Lifecycle", "service": "olx-lifecycle.service"},
    "watchlist": {"label": "Watchlist Lifecycle", "service": "olx-watchlist-lifecycle.service"},
    "followup": {"label": "CRM Follow-up", "service": "olx-followup.service"},
    "sale-monitor": {"label": "Sale Monitor", "service": "olx-sale-monitor.service"},
    "daily-report": {"label": "Daily Report", "service": "olx-daily-report.service"},
    "backup": {"label": "Backup", "service": "olx-backup.service"},
    # Jednostka może być instalowana osobno i nie musi istnieć na każdej maszynie.
    "facebook": {"label": "Facebook Marketplace", "service": "facebook-flip.service"},
}

AUTH_REQUIRED = os.getenv("DASHBOARD_AUTH_REQUIRED", "1").strip().lower() not in {
    "0", "false", "no", "off"
}
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "")
COOKIE_SECURE = os.getenv("DASHBOARD_COOKIE_SECURE", "0").strip().lower() in {
    "1", "true", "yes", "on"
}
REFRESH_SECONDS = max(5, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15")))
