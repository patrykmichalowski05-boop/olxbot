# FlipRadar — GUI (mobile)

## Stack

- Expo SDK 57, React Native 0.86, TypeScript
- Expo Router (`mobile/src/app`)
- TanStack Query (stan serwera)
- React Hook Form + Zod (formularze)
- Expo SecureStore (sesja na iOS/Android; web live tylko z `EXPO_PUBLIC_FLIP_WEB_LIVE=1`, inaczej demo)

## Struktura

```text
mobile/src/
  app/           # nawigacja (tabs + stack)
  components/    # AppScreen, ProductCard, …
  features/      # auth, opportunity, radar filters
  api/           # klient live + demo, typy, mappery
  hooks/
  theme/
  utils/
  test/
```

## Uruchomienie

```bash
cd mobile
cp .env.example .env
npm install
npx expo start
```

- **Podgląd web (domyślnie DEMO):** `npx expo start --web`
- **Live API:** ustaw `EXPO_PUBLIC_FLIP_API_URL` (HTTPS), `EXPO_PUBLIC_FLIP_APP_MODE=live`, na telefonie zaloguj się kontem z `flip_core` auth DB.
- **Deals / flipy finansowe:** backend PostgreSQL + `EXPO_PUBLIC_FLIP_WORKSPACE_ID`.

## Nawigacja

Dolne zakładki: Radar, Obserwowane, Analizuj, Moje flipy, Ustawienia.

Stack: szczegóły oferty, filtry (sheet), powiadomienia, zakup, deal, analityka.

## Tryby

| Tryb | Kiedy | Mutacje |
|------|--------|---------|
| DEMO | brak HTTPS API, web bez `FLIP_WEB_LIVE`, lub `FLIP_APP_MODE=demo` | Lokalny `demoClient`, cache Query oddzielny przez `api.mode` w kluczach |
| LIVE | skonfigurowane API + sesja | Auth refresh (pojedynczy retry 401), v2 deals z Idempotency-Key |

## Funkcje live vs demo

| Funkcja | Live | Demo |
|---------|------|------|
| Logowanie / refresh / logout | Tak | Symulacja sesji |
| Radar + paginacja | Tak | Fixtures (auta, PC, buty, słaba wycena, niedostępne) |
| Szczegóły oferty | `listings/{id}` | Fixtures |
| Watchlist universal | Tak (gdy bridge) | Tak |
| Analiza manual | Sync API | Job symulowany |
| Flipy v2 | Wymaga workspace + PG | Lokalna lista demo |
| Powiadomienia | Brak API | Fixtures |
| Push / share menu | Nie zaimplementowano (wymaga native) | — |

## Testy

```bash
npm run typecheck
npm test
```

## Weryfikacja natywna

Push, SecureStore i kamera wymagają builda dev client / urządzenia. Web potwierdza układ, nawigację i demo — nie zastępuje testów iOS/Android (`mobile/DEVICE_TEST.md`).

## Zachowanie starego klienta

Poprzednie pliki (`App.tsx`, `src/RadarPanel.tsx`) pozostają w repo jako referencja; entrypoint aplikacji to `expo-router/entry`.
