# FlipRadar (Expo)

Uniwersalny klient mobilny do oceny okazji flipowych — **FlipRadar**.

Panel bota ma jasny motyw, boczną nawigację na komputerze, menu na telefonie, zwartą listę radaru i osobne widoki wyników oraz danych rynku. [Opis i konfiguracja nowego UI](../docs/BOT_UI_REDESIGN.md). W ustawieniach nadal można wybrać motyw ciemny.

Na web adres `/` otwiera publiczną stronę FlipRadar. Przycisk „Przejdź do bota” prowadzi przez konto do prywatnego radaru. [Strona, rejestracja, pakiety i wdrożenie](../docs/PORTAL_SETUP.md) korzystają z tego samego Expo Router i backendu. Dla tego wariantu użyj `portal.env.example`; domyślna konfiguracja dotychczasowej aplikacji pozostaje osobna.

Szczegóły implementacji: [GUI_IMPLEMENTATION.md](./GUI_IMPLEMENTATION.md)
Luki API: [FRONTEND_BACKEND_GAPS.md](./FRONTEND_BACKEND_GAPS.md)

Zapisane modele i powiadomienia: [konfiguracja uniwersalnego radaru](../docs/UNIVERSAL_SETUP.md).
Ekran **Ustawienia → Moje wyszukiwania i alerty** wymaga włączenia nowego modułu API przez `FLIP_HUNTER_DB`.

## Szybki start

```bash
cd mobile
cp .env.example .env
npm install
npx expo start
```

Bez konfiguracji API aplikacja startuje w **trybie DEMO** (web i symulator).

## Konfiguracja live

1. `EXPO_PUBLIC_FLIP_API_URL=https://twoj-host` (HTTPS)
2. Opcjonalnie `EXPO_PUBLIC_FLIP_RADAR_SOURCE=universal`
3. Dla flipów PostgreSQL: `EXPO_PUBLIC_FLIP_WORKSPACE_ID=...`
4. Na urządzeniu: logowanie jak w dev API (`flip_core` AuthStore)

Diagnostyka TLS: `python scripts/check_https_api.py`

## Skrypty

- `npm run typecheck`
- `npm run lint`
- `npm test`
- `npm run web` / `npm run android` / `npm run ios`
