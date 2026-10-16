# Zmienione pliki: strona i konta FlipRadar

Łącznie **70 plików** względem poprzedniej paczki (`9ce9337`). Pełny kod w archiwum zawiera również wcześniejszy uniwersalny radar i jego dokumentację.

Przebudowano stronę publiczną, rejestrację i logowanie web, przejście do bota oraz ekran konta. Dodano pakiety i kontrolę dostępu w API, panel właściciela, kolektor kont oraz prywatne powiadomienia. Wspólne komponenty zachowują ciemny wygląd bota; poprawiono też konfigurację ESLint i wskazane przez nią drobne problemy w istniejących komponentach.

## Strona i dostęp w aplikacji

- `mobile/src/UniversalPanel.tsx`
- `mobile/src/app/(auth)/login.tsx`
- `mobile/src/app/(tabs)/_layout.tsx`
- `mobile/src/app/(tabs)/flips/index.tsx`
- `mobile/src/app/(tabs)/settings/index.tsx`
- `mobile/src/app/+html.tsx`
- `mobile/src/app/_layout.tsx`
- `mobile/src/app/account.tsx`
- `mobile/src/app/bot.tsx`
- `mobile/src/app/flips/[dealId].tsx`
- `mobile/src/app/index.tsx`
- `mobile/src/app/info.tsx`
- `mobile/src/app/purchase/[listingId].tsx`
- `mobile/src/app/register.tsx`
- `mobile/src/app/searches/index.tsx`
- `mobile/src/features/portal/AccountAccessBoundary.tsx`
- `mobile/src/features/portal/PortalPage.tsx`
- `mobile/src/features/portal/PortalPage.web.tsx`
- `mobile/src/features/portal/content.ts`
- `mobile/src/features/portal/navigation.ts`
- `mobile/src/features/portal/portal.css`
- `mobile/src/features/portal/types.ts`

## Sesja, API, wspólne komponenty i narzędzia

- `mobile/.env.example`
- `mobile/README.md`
- `mobile/eslint.config.js`
- `mobile/portal.env.example`
- `mobile/src/api/client.ts`
- `mobile/src/api/endpoints/auth.ts`
- `mobile/src/api/endpoints/deals.ts`
- `mobile/src/api/endpoints/portal.ts`
- `mobile/src/api/errors.ts`
- `mobile/src/api/index.ts`
- `mobile/src/api/session.ts`
- `mobile/src/components/ConfidenceIndicator.tsx`
- `mobile/src/components/ConfirmationSheet.tsx`
- `mobile/src/components/DemoBanner.tsx`
- `mobile/src/components/FilterSheet.tsx`
- `mobile/src/components/LoadingSkeleton.tsx`
- `mobile/src/components/ProductCard.tsx`
- `mobile/src/features/auth/AuthContext.tsx`
- `mobile/src/test/portal-navigation.test.ts`
- `mobile/src/types/styles.d.ts`
- `mobile/src/utils/config.ts`

## Backend kont i kolektor

- `flip_core/auth_store.py`
- `universal_v2/hunter/api.py`
- `universal_v2/hunter/runner.py`
- `universal_v2/hunter/store.py`
- `universal_v2/mobile_bridge.py`
- `universal_v2/portal/__init__.py`
- `universal_v2/portal/admin.py`
- `universal_v2/portal/collector.py`
- `universal_v2/portal/plans.py`
- `universal_v2/portal/routes.py`
- `universal_v2/portal/store.py`
- `universal_v2/portal/web.py`

## Testy backendu

- `tests/test_portal_access.py`
- `tests/test_portal_collector.py`
- `tests/test_portal_http.py`
- `tests/test_portal_web.py`

## Konfiguracja, dokumentacja i CI

- `.github/workflows/backend-dev.yml`
- `.github/workflows/universal-hunter.yml`
- `PORTAL.env.example`
- `README.md`
- `docs/PORTAL_CHANGED_FILES.md`
- `docs/PORTAL_SETUP.md`
- `docs/PORTAL_VALIDATION.md`
- `docs/UNIVERSAL_SETUP.md`
- `examples/generate_portal_demo.py`
- `ops/systemd/flipradar-portal-collector.service.example`
- `ops/systemd/flipradar-portal-web.service.example`
