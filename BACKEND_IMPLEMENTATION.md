# Backend — stan implementacji (skrót dla frontendu)

Pełny opis etapów developerskich: katalog [`docs/`](docs/).

## API mobilne `/api/v1` (dev)

Implementacja: `flip_core/mobile_api.py` + montowanie mostów `universal_v2/mobile_bridge.py`.

- Auth z rotacją refresh: [`docs/BACKEND_AUTH_AND_RADAR.md`](docs/BACKEND_AUTH_AND_RADAR.md)
- Universal radar / watchlist / manual: `universal_v2/*_routes.py`
- Brak publicznego OpenAPI w produkcji dev (`openapi_url=None` w mobile API)

## API PostgreSQL `/api/v2`

Implementacja: `backend/app/api/app.py` — transakcje flipów (zakup, koszty, sprzedaż, events).

Etapy migracji: `docs/BACKEND_STAGES_*.md`.

## Panel Flask V2

Niezależny od klienta mobilnego: `webapp_v2.py`, `app_v2/` — pozostaje bez zmian.

## Zmienne środowiska (API mobilne)

- `FLIP_API_AUTH_DB`
- `FLIP_API_DATA_ROOT`

Szczegóły uruchomienia smoke: `ops/dev/smoke_mobile_api.py`.

Frontend mobilny **nie modyfikuje** skanerów, wyceny ani systemd.
