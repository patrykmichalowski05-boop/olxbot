# Połączenie kodu z GitHuba z nowym GUI

Integracja oparta na `main` z commitu `3e31b881d110bcaad01627d589528b735cc5db9d` (16.10.2026). Źródłem GUI jest obecny `mobile/` w tym katalogu, z zachowanym wyglądem nowego panelu, strony wejściowej, logowania i konta. Nie należy kopiować na niego całej starszej paczki backendu.

## Co wykazał przegląd

- Serwer uruchamia Flask przez `flip_v2_overlay_dev.py`. Importuje `webapp_v2` oraz nakładki V1–V11. Obecna sesja i konta pochodzą z `multiuser_v2` / `accounts_v10`.
- GUI było już w repozytorium, ale eksport nie zawierał śledzonych fontów i ikon, odświeżenie dynamicznych adresów kończyło się błędem, a prywatny radar i skrzynka nie obsługiwały kolejnych stron.
- Formularz GUI pokazywał operacje starszego backendu universal, których serwer V10/V12 nie realizuje. Nie można było traktować pustej odpowiedzi jako działającej watchlisty.
- Globalny bot zapisuje wyniki do `offer_snapshots.db`, CRM do `deal_crm.db`, a faktyczne zakupy i sprzedaże do `flip_results.db`. Prywatne wyszukiwania używają osobnych tabel V4/V7/V9 z `owner_id`.
- `active/flipradar-portal/source/` oraz `active/flipradar-universal/app/` zawierają inne, starsze warianty serwera. Nie są źródłem logowania bieżącej instalacji.

Skanery, harmonogramy, powiadomienia wysyłane przez bota, algorytmy wyceny i dotychczasowe trasy narzędzi nie zostały przebudowane.

## Zakres połączenia

| Funkcja | Zachowanie |
| --- | --- |
| Logowanie / rejestracja / wylogowanie | Dotychczasowe konta V10 i cookie sesji Flask; bez drugiej bazy kont |
| Strona wejściowa i przycisk przejścia do bota | Nowe GUI; dostęp sprawdzany przez istniejącą tożsamość konta |
| Radar zwykłego użytkownika | Oferty własnych aktywnych wyszukiwań V9; wyszukiwanie i paginacja, dokładność ceny do groszy |
| Prywatne wyszukiwania | OLX, kategorie obsługiwane przez V7, opcjonalny budżet; limity User 3 / MiniFliper 7 / Fliper bez limitu |
| Zapis wyszukiwania | Istniejące tabele V4/V7; ponowienie tego samego klucza nie tworzy duplikatu; limit sprawdzany w transakcji |
| Powiadomienia w GUI | Odczyt własnych alertów V8 z paginacją; bez zmiany wysyłki Telegram / e-mail / harmonogramów |
| Globalny radar | Tylko główne konto `root`; odczyt istniejących snapshotów i wycen; filtry przed paginacją |
| Globalny magazyn i analityka | Odczyt tylko dla `root` lub roli `admin`; koszt zakupu, koszty dodatkowe i przygotowanie do sprzedaży |
| Niepełne dane finansowe | Znak „—” i informacja o brakujących kwotach, bez prezentowania braku zakupu jako kapitału 0 zł |
| Zakupy, koszty, sprzedaż, watchlista, analiza ręczna | Zapis nadal w dotychczasowym centrum narzędzi. GUI nie wysyła nieobsługiwanych mutacji |
| Pozostałe platformy w prywatnym formularzu | Widoczne dopiero po rzeczywistym udostępnieniu przez backend; ta integracja nie dodaje skanerów Allegro Lokalnie, Otomoto ani Vinted |
| Tryb podglądu | Nowe mutacje GUI zablokowane na serwerze; logowanie / wznowienie / wylogowanie pozostają możliwe |

Nowe pole `capabilities` w konfiguracji publicznej i danych konta opisuje funkcje serwera. Jest dodatkiem do odpowiedzi; istniejące nazwy tras i pól pozostają. Klient nadal obsługuje starszy backend universal, który nie zwraca tego pola.

Identyfikator tokenu `flask-session` nie daje sam w sobie dostępu. Serwer wymaga ważnej sesji i aktywnego konta; zapisy wymagają tego samego originu i nagłówka klienta. Odczyty globalnych baz korzystają z SQLite `mode=ro` i `query_only`, bez migracji ani tworzenia brakującej bazy. Zapis prywatnych wyszukiwań zachowuje istniejącą tabelę kluczy ponowień V12.

ROI i wynik na kartach globalnego radaru pochodzą z wyceny / adaptera, w tych samych jednostkach co filtry. Prywatny V9 nie dostarcza takich wycen — GUI nie generuje dla niego fikcyjnego zarobku.

## Budowanie GUI z aktualnego Git

Wymagane: Node.js 22+ oraz Python 3.10+. Z katalogu głównego repozytorium:

```bash
python3 active/flipradar-v12/build_ui.py --install
```

Skrypt uruchamia `npm ci` i eksport Expo w konfiguracji live dla obecnego serwera. API jest pod tym samym adresem co strona, więc nie trzeba wpisywać domeny do bundle'a. Folder `dist/` zawiera gotowy eksport. Dotychczasowy eksport jest odkładany do ignorowanego katalogu `.dist-backup-*`; błędny build go nie zastępuje. Build nie restartuje usług ani nie aktywuje produkcji.

Można wskazać osobny wynik, np. na potrzeby CI:

```bash
python3 active/flipradar-v12/build_ui.py --output /tmp/flipradar-gui
```

Historyczny `deploy_v12.py prepare` odtwarza zamrożoną paczkę archiwalną. **Do aktualnego kodu z Git używaj `build_ui.py`**, aby nie cofnąć źródeł do starego ZIP-a. Dotychczasowy proces publikacji ma też poprawione kopiowanie i rollback nowego modułu odczytu danych; nie został uruchomiony w ramach tej integracji.

## Brakujące źródła bieżącej instalacji

W tym commicie GitHuba nie ma następujących plików importowanych przez istniejący punkt wejścia:

```text
flip_gui_data_dev.py
personal_inventory_v1.py
premium_radar_v2.py
premium_inventory_stats_v2.py
multiuser_v2.py
user_one_search_v3.py
workspace_v4_live.py
flipradar_gui_v5.py
guide_v7.py
monitor_v8_web.py
flipradar_user_web_v9.py
accounts_v10.py
v11_ui.py
```

Muszą pochodzić z rzeczywistego serwera, zwykle `/opt/olx-bot-budget-dev`. Ich pośrednie importy, szablony i obecne zależności Pythona także muszą być dostępne. Diagnostyka sprawdza obecność i składnię bez wykonywania modułów; nie potwierdza całej instalacji ani zgodności produkcyjnego schematu bazy. Nie kopiuj do Git baz, plików `.env`, haseł, sesji ani kluczy.

Na serwerze z obecną instalacją:

```bash
python3 active/flipradar-v12/runtime_check.py \
  --bot-root /opt/olx-bot \
  --overlay-root /opt/olx-bot-budget-dev
```

Wynik `ready: false` i kod 2 wskazują brakujące pliki / eksport / fonty. Fabryka WSGI odmawia startu przy takiej konfiguracji, zamiast uruchamiać zastępcze logowanie.

## Podgląd przy obecnym środowisku serwera

Użyj tego samego środowiska Pythona i konfiguracji, które uruchamiają obecny serwer. Ze świeżego checkoutu, w którym zbudowano GUI:

```bash
export OLX_BOT_DIR=/opt/olx-bot
export FLIPRADAR_OVERLAY_DIR=/opt/olx-bot-budget-dev
export FLIPRADAR_LEGACY_DATA_ROOT=/opt/olx-bot
export FLIPRADAR_GUI_MODE=stage
gunicorn --pythonpath active/flipradar-v12 \
  --bind 127.0.0.1:8094 'gui_entry:create_app()'
```

`stage` jest domyślny i blokuje zapisy przez nowe API GUI, także jeśli nakładka była wcześniej instalowana w trybie live. Nadal korzysta z istniejącego logowania oraz odczytów. Dotychczasowe trasy centrum narzędzi należą do starej aplikacji i zachowują jej zachowanie; ten tryb nie jest kopią ani izolowaną bazą testową całego bota. Import istniejącego serwera może wykonywać jego dotychczasową inicjalizację. Do próby całego środowiska używaj jego obecnej procedury stagingowej.

Ta integracja nie przełącza reverse proxy, nie zmienia usług i nie tworzy flagi `/opt/olx-bot-budget-dev/.v12_live`. Tryb `live` zachowuje istniejący mechanizm aktywacji V12 tą flagą. Ewentualne przełączenie trzeba wykonać dotychczasową procedurą wdrożenia po sprawdzeniu rzeczywistych modułów V10.

## Weryfikacja

```bash
cd active/flipradar-v12/mobile
npm ci
npm run typecheck
npm run lint
npm test -- --runInBand
```

Z katalogu głównego, w środowisku z Flask i pytest:

```bash
python3 -m pytest active/flipradar-v12/tests -q
```

Testy adaptera korzystają z tymczasowych baz SQLite i jawnych atrap interfejsu `multiuser_v2` / `accounts_v10`, ponieważ rzeczywistych źródeł V10 nie ma w repozytorium. Sprawdzają cookie, brak dostępu samym tokenem, origin zapisów, izolację właściciela, odwołanie sesji, paginację, grosze, limity równoległych zapisów, uprawnienia administratora oraz blokady trybu podglądu. Testy gotowego eksportu sprawdzają dostępność stron, skryptów, CSS, fontów i obrazów przez Flask.

Workflow `.github/workflows/gui-integration.yml` uruchamia testy mostka, TypeScript, lint, testy klienta i świeży eksport. Nie wdraża aplikacji. Starszy workflow repozytorium pozostaje niezależny.

Weryfikacja tej zmiany obejmuje także istniejące testy `tests/` w katalogu głównym. Nie uruchamiano skanerów, wysyłki powiadomień ani zapisów na VPS. Pełne logowanie produkcyjne wymaga sprawdzenia z brakującymi źródłami serwera. Interfejs zachowuje Expo i React Native, lecz adapter sesji Flask opisany tutaj dotyczy **web**. Dostęp live na iOS/Android wymaga osobnego podłączenia natywnej sesji; nie był testowany w tej integracji.

Wyniki lokalnej weryfikacji tej zmiany: **93 testy klienta, 31 testów integracji V12 i 80 istniejących testów bota** przeszły. `npm run typecheck`, `npm run lint` i eksport Expo web zakończyły się powodzeniem. Nie wykonano przeglądu w prawdziwej przeglądarce ani na urządzeniu mobilnym.

## Pliki i obszary zmian

| Pliki | Zmiana |
| --- | --- |
| `v12_bridge.py` | Sesja, uprawnienia, paginacja, ceny w groszach, dynamiczne adresy, capabilities i odczyt globalnego radaru |
| `flipradar_legacy_bridge.py` | Odczyt istniejących snapshotów, magazynu i finansów dla administratora |
| `gui_entry.py`, `runtime_check.py`, `build_ui.py` | Punkt wejścia, diagnostyka braków i build z obecnych źródeł |
| `deploy_v12.py` | Publikacja i odtwarzanie także modułu odczytu danych |
| `mobile/src/features/runtime/*` | Sprawdzanie funkcji konta, stany oczekiwania / błędu, blokady niedostępnych zapisów |
| `mobile/src/features/workspace/{hooks.ts,BotShell.tsx,dealSummary.ts}` | Użycie możliwości serwera, pasek podglądu, rzetelne podsumowania finansowe |
| `mobile/src/features/portal/{PortalPage.web.tsx,types.ts}` | Strona wejściowa, logowanie, konto i administracja dopasowane do V10 |
| `mobile/src/api/endpoints/radar.ts`, `mobile/src/api/{types/radar.ts,mappers/opportunity.ts,mappers/deal.ts}` | Filtry radaru i opcjonalne dane adaptera bez zmiany starszych kontraktów |
| `mobile/src/app/(tabs)/{radar,watched,analyze,flips}/index.tsx` | Radar i ekrany zgodne z możliwościami serwera |
| `mobile/src/app/searches/{index.tsx,results.tsx}`, `mobile/src/app/analytics/index.tsx` oraz strony `offer`, `purchase`, `flips/[dealId]` | Prywatne formularze, szczegóły i magazyn |
| `tests/*`, `mobile/src/test/{runtime-integration,hunter-mapper}.test.ts` | Testy integracji i regresji |
| `dist/*` | Przebudowany eksport wraz z wcześniej pomijanymi assetami |
| `../../.github/workflows/gui-integration.yml`, `../../.gitignore`, `../../README.md` | CI, śledzenie assetów i mapa repozytorium |

Pełną listę ścieżek w gałęzi integracji pokazuje `git diff --name-status main...HEAD`.
