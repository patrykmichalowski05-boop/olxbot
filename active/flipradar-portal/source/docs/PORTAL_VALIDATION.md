# Weryfikacja strony i kont FlipRadar

Data: 16 października 2026. Zmiany na lokalnej gałęzi `feature/flipradar-public-portal-20261016`, z bazą `9ce9337ce21b294c0029f3f5ae650bd87920f0ca` poprzedniej paczki uniwersalnego bota.

## Wykonane sprawdzenia

| Sprawdzenie | Wynik |
| --- | --- |
| Pełna regresja `python -m pytest tests -q` | **455 passed, 8 skipped, 53 subtests passed** |
| Oddzielne minimalne środowisko `requirements-universal-test.txt` | **123 passed**: testy hunter i portal |
| `npm run typecheck` | Bez błędów |
| `npm run lint` | Bez błędów i ostrzeżeń ESLint |
| `npm test -- --runInBand` | **50 passed**, 9 zestawów |
| `npx expo export --platform all` z włączonym portalem live | Eksport web oraz pakiety iOS / Android |
| Ruff: moduły hunter, portal, generatory i testy | Bez błędów reguł `E4,E7,E9,F,I` |
| `git diff --check` | Bez błędów whitespace |
| Statyczny HTML eksportu | Polski język, tytuły, wyszukiwarka, 3 kroki, 3 pakiety, 4 FAQ, CTA do bota i istniejący plik CSS |

Testy kont obejmują: brak awansu do administratora przez rejestrację, zapis pakietu i zużycia, równoległe żądania bez przekroczenia limitu, wycofanie zużycia po błędzie, bezpieczne ponowienia, ręczną aktywację przez właściciela, wygaśnięcie i blokadę, migrację dotychczasowych kont, rejestrację dopiero po utworzeniu właściciela, cookies, odrzucenie obcego origin, wznowienie wielu kart i unieważnienie ich przy wylogowaniu. Sprawdzono także rozdzielenie profili, radaru i powiadomień między kontami oraz brak ujawniania prywatnych kosztów przez publiczne porównania.

Kolektor sprawdzono na źródle offline: Start otrzymuje radar bez nowych alertów, Standard tworzy alert wyłącznie dla właściwego konta, a konta wygasłe, zablokowane i nieprzypisane są pomijane. Generator danych nie tworzy domyślnych danych logowania.

## Granice tej weryfikacji

Osiem pominiętych testów wymaga oddzielnego PostgreSQL. Konfiguracja CI nadal zawiera usługę i zadanie tych testów, lecz nie uruchamiano jej na GitHubie w tej sesji. Lokalny test z minimalnym środowiskiem zgłosił jedno ostrzeżenie zależności Starlette o przyszłej zmianie transportu TestClient; wszystkie testy przeszły.

Nie było dostępnego wspieranego narzędzia przeglądarkowego do projektu. Sprawdzono eksport i jego HTML, ale **nie wykonano wizualnego przeglądu ani klikania w przeglądarce**. Eksport iOS/Android potwierdza kompilację; nie zastępuje testu na urządzeniu. Stany formularzy i decyzje serwera sprawdzono testami HTTP oraz testami TypeScript.

Nie wysyłano Telegrama, nie pobierano ofert z kont marketplace, nie wykonano transakcji ani płatności. Dostęp live do pięciu serwisów wymaga konfiguracji i weryfikacji opisanej w `UNIVERSAL_SETUP.md`. Nie zmieniano działających usług, domen ani zdalnego repozytorium. Kod zawiera ręczną aktywację pakietów, bez integracji operatora płatności.

## Powtórzenie

```bash
python -m pytest tests/test_hunter_*.py tests/test_portal_*.py -q
cd mobile
npm run typecheck
npm run lint
npm test -- --runInBand
npx expo export --platform all
```

Pełna regresja wymaga zależności starego backendu. Instalację i konfigurację opisuje `PORTAL_SETUP.md`.
