# FlipRadar (Expo)

Uniwersalny klient mobilny do oceny okazji flipowych — **FlipRadar**.

Szczegóły implementacji: [GUI_IMPLEMENTATION.md](./GUI_IMPLEMENTATION.md)
Luki API: [FRONTEND_BACKEND_GAPS.md](./FRONTEND_BACKEND_GAPS.md)

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
- `npm test`
- `npm run web` / `npm run android` / `npm run ios`
