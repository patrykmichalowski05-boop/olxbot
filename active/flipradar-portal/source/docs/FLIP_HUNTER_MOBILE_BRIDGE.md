# Etapy techniczne 32-36 — integracja API

Glowny etap 4: integracja testowa z istniejacym FastAPI.
Glowny etap 5: iOS/Android NIEZALICZONY.
Glowny etap 6: integracje i komercjalizacja NIEZALICZONE.

Punkt wejscia:
universal_v2.mobile_bridge:create_app

Wykorzystuje logowanie flip_core.mobile_api.
Dane developerskie sa w osobnym katalogu.

Nowe sciezki:
/api/v1/universal/status
/api/v1/universal/radar
/api/v1/universal/manual/analyze
/api/v1/universal/watchlist
/api/v1/universal/watchlist/close

Zmienne:
FLIP_API_AUTH_DB
FLIP_API_DATA_ROOT
FLIP_UNIVERSAL_DEV_DIR

Reczna analiza jest domyslnie wylaczona.
Aby ja wlaczyc w odizolowanym tescie:
FLIP_UNIVERSAL_ENABLE_MANUAL=1

Brak potwierdzonych danych rynkowych:
NO_RELIABLE_VALUATION.

Brak automatycznego pobierania ofert.
Brak wdrozonego push i publicznego HTTPS.

Aplikacja mobilna nie korzysta jeszcze z nowych tras.
Nie zmieniaj produkcyjnych URL ani plikow systemd.
