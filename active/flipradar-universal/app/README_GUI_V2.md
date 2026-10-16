# OLX Flip Hunter — Control Center V2

Nowy panel działa obok starego `dashboard.py`. Nie zmienia skanerów ani algorytmu wyceny.

## Co obejmuje

- wspólny dashboard OLX + Facebook Marketplace,
- lista i filtrowanie alertów,
- szczegóły wyceny `valuation_v3`, exact market, same-GPU, neighbor GPU i sanity cap,
- decyzje `deal_action`, opening i max buy,
- pytania do sprzedającego i warianty negocjacji,
- CRM oraz historia negocjacji,
- follow-upy,
- watchlista,
- checklista przed zakupem,
- rejestracja zakupu i sprzedaży,
- checklista odbioru,
- koszty przygotowania do sprzedaży,
- automatyczne ceny sprzedaży,
- generator ogłoszeń OLX/Facebook,
- tracker aktywnego ogłoszenia i zmian ceny,
- magazyn,
- analityka realnego zysku,
- market.db,
- health/watchdog,
- podgląd logów systemd,
- ręczne uruchamianie wyłącznie dozwolonych usług systemd.

## Bezpieczeństwo

Panel V2 domyślnie wymaga hasła. Nie uruchomi części prywatnej bez `DASHBOARD_PASSWORD`.
Wszystkie mutujące formularze są chronione tokenem CSRF. Akcje systemd korzystają ze stałej allowlisty; nazwa usługi nie pochodzi bezpośrednio z requestu.

## Instalacja obok obecnego dashboardu

Skopiuj zawartość paczki do katalogu repo:

```bash
cd /opt/olx-bot
# skopiuj: app_v2/, templates_v2/, static_v2/, webapp_v2.py
```

Dodaj do `/opt/olx-bot/.env`:

```bash
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD='ustaw-mocne-haslo'
DASHBOARD_SECRET_KEY='ustaw-dlugi-losowy-sekret'
DASHBOARD_AUTH_REQUIRED=1
DASHBOARD_COOKIE_SECURE=0
DASHBOARD_REFRESH_SECONDS=15
```

Losowy sekret możesz wygenerować:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Zainstaluj usługę testową na porcie 8089:

```bash
cp /opt/olx-bot/systemd/olx-dashboard-v2.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now olx-dashboard-v2.service
systemctl status olx-dashboard-v2.service --no-pager
```

Panel będzie pod:

```text
http://ADRES_SERWERA:8089
```

Stary panel na `8088` pozostaje bez zmian.

## Logi

```bash
journalctl -u olx-dashboard-v2.service -f
```

## Test ręczny przed przełączeniem produkcji

Sprawdź kolejno:

1. logowanie,
2. `/offers` i szczegóły kilku ofert,
3. CRM i zmianę statusu,
4. watchlistę,
5. zapis testowego follow-upu,
6. system/health,
7. logi usług,
8. uruchomienie FAST z panelu,
9. istniejący zakup/sprzedaż tylko na rekordzie, na którym faktycznie chcesz zmienić stan.

Po weryfikacji można zmienić istniejący `olx-dashboard.service` z `dashboard:app` na `webapp_v2:app` i port z 8089 na 8088.

## Struktura

```text
webapp_v2.py
app_v2/
    __init__.py
    config.py
    db.py
    security.py
    services.py
    routes.py
templates_v2/
    base.html
    login.html
    setup_required.html
    dashboard.html
    offers.html
    offer.html
    watchlist.html
    crm.html
    inventory.html
    analytics.html
    market.html
    system.html
    logs.html
static_v2/
    app.css
    app.js
systemd/
    olx-dashboard-v2.service
```

## Ważne

Obecne moduły `sale_prep`, `purchase_checklist`, `pickup_checklist`, `crm_history`, `crm_followup`, `sale_listing_tracker` mają ścieżki `/opt/olx-bot/...` wpisane na stałe. V2 zachowuje z nimi zgodność. Dalszym krokiem technicznym powinno być przeniesienie ścieżek wszystkich baz do jednego `config.py` w całym projekcie.
