# Luki kontraktu API (FlipRadar frontend)

Dokument uzupełnia brak formalnego OpenAPI w repo. Frontend implementuje wyłącznie endpointy obecne w kodzie (`flip_core/mobile_api.py`, `universal_v2/*`, `backend/app/api/app.py`).

## Brakujące lub niepełne względem specyfikacji produktowej

| Obszar | Wymagane przez GUI | Stan backendu | Działanie frontendu |
|--------|-------------------|---------------|---------------------|
| OpenAPI `/api/v1` | Pełny kontrakt | Brak pliku OpenAPI | Typy wyprowadzone z kodu i testów |
| `GET /api/v2/workspaces/{workspace_id}/notifications` | Skrzynka powiadomień | Dostępne z paginacją | Live pobiera zdarzenia PostgreSQL; brak stanu odczytu i push |
| `POST /api/v1/imports/jobs` + polling | Analiza linku/pliku z `job_id` | Manual analyze synchroniczne | Demo symuluje `job_id`; live pokazuje odpowiedź synchroniczną |
| Profile wyszukiwania (serwer) | Zapis profili filtrów | Brak | Profile w `AsyncStorage` |
| Filtry radaru (serwer) | sort, ROI, kategoria, źródła | Radar: `q`, `limit`, `before_id` | Filtry sort/kategoria/platforma po stronie klienta |
| `GET /api/v1/categories` / źródła | Dynamiczne podkategorie | Brak | Stałe kategorie UI + platformy z filtra |
| Workspace list | Wybór workspace | Brak listy; v2 wymaga `workspace_id` | `EXPO_PUBLIC_FLIP_WORKSPACE_ID` |
| Push / devices | Rejestracja urządzenia | Brak w v1 dev API | Sekcja w ustawieniach — niedostępne |
| Porównania rynku w detail | Osobny endpoint comparisons | Częściowo w JSON snapshot | Mapowanie z `listings/{id}` + luka na structured comparisons |
| Offline queue mutacji | Kolejka zakupów | Brak | Formularze zachowane; zapis blokowany z komunikatem w live bez sieci |

## Istniejące endpointy używane przez klienta

- Auth: `POST /api/v1/auth/login`, `refresh`, `logout`; `GET /api/v1/me`
- Radar: `GET /api/v1/radar` lub `GET /api/v1/universal/mobile-radar`
- Listings: `GET /api/v1/listings`, `GET /api/v1/listings/{id}`, `GET .../history`
- Universal: watchlist GET/POST, close, `POST /api/v1/universal/manual/analyze`
- Valuations: `POST /api/v1/valuations/preview` (kalkulator — do podpięcia w kolejnej iteracji UI)
- Deals v2: `GET/POST /api/v2/workspaces/{id}/deals`, costs, sell, events (gdy skonfigurowany PG)

## Propozycja minimalnego uzupełnienia kontraktu

1. OpenAPI 3.1 dla `/api/v1` i `/api/v2` wygenerowane z FastAPI (`openapi_url` w dev).
2. `GET /api/v1/workspaces` + aktywny workspace w `/me`.
3. `GET /api/v1/notifications` z paginacją i `read`.
4. `POST /api/v1/imports/jobs` + `GET /api/v1/imports/jobs/{id}` ze statusami bez fake progress %.
5. Radar query params: `category`, `sort`, `min_profit_minor`, `sources[]`.
