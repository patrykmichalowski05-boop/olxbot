# FlipRadar: strona początkowa i dostęp przez konto

## Co zawiera kod

Jasna strona publiczna jest zbudowana w istniejącym Expo Router, bez drugiego projektu frontendowego. Zawiera wyszukiwarkę cen, trzy kroki, przykład wyniku, cennik, FAQ i przycisk „Przejdź do bota”. Układ dopasowuje się do telefonu i komputera. Radar po zalogowaniu zachowuje ciemny interfejs aplikacji.

| Adres web | Działanie |
| --- | --- |
| `/` | Publiczna strona początkowa |
| `/login` | Logowanie |
| `/register` | Rejestracja konta Start |
| `/bot` | Sprawdzenie dostępu i przejście do radaru |
| `/account` | Pakiet, limit, ważność i zgłoszenie aktywacji; dla właściciela zarządzanie kontami |
| `/searches` | Własne modele, platformy, koszty i progi powiadomień |
| `/radar` | Oferty przypisane do konta |
| `/info?topic=privacy` | Informacje o danych i sesji |

HTML i CSS strony występują tylko w wariancie `.web.tsx`. iOS i Android używają komponentów React Native, w tym natywnego ekranu konta. Istniejący formularz logowania na urządzeniach pozostaje dostępny. Nowe konta zakłada się na stronie webowej; te same dane logowania działają w aplikacji.

## Pakiety i aktywacja

| Pakiet | Cena przykładowa | Limit w okresie pakietu | Ważność | Nowe powiadomienia |
| --- | --- | --- | --- | --- |
| Start | 0 zł | 3 | Bezterminowo | Nie |
| Standard | 19 zł | 20 | 30 dni od aktywacji | Tak |
| Plus | 39 zł | 60 | 90 dni od aktywacji | Tak |
| Dotychczasowy dostęp | — | Bez limitu | Jak w poprzedniej instalacji | Tak |

Ceny i nazwy są przykładem z dostarczonego wzoru. Wybór Standard lub Plus zapisuje zgłoszenie `PENDING`. Dopiero właściciel aktywuje pakiet na stronie `/account` lub przez lokalne narzędzie administracyjne. **Nie ma bramki płatniczej, automatycznego obciążenia ani udawanego potwierdzenia zakupu.**

Jedno udane publiczne porównanie cen albo nowy zapisany model wykorzystuje jedno wyszukiwanie. Zmiana modelu, wariantu, kategorii lub platform też wykorzystuje wyszukiwanie. Zmiana samych kosztów, nazwy, progów zysku lub wstrzymanie profilu nie pobiera kolejnego. Powtórzenie tej samej operacji po błędzie połączenia nie nalicza jej drugi raz. Błąd zapisu lub porównania wycofuje zużycie. Brak pasujących wyników jest wykonanym porównaniem i zużywa wyszukiwanie.

Zużycie całego limitu blokuje nowe wyszukiwania, ale pozwala czytać dotychczasowy radar do końca ważności. Wygaśnięcie lub wstrzymanie dostępu blokuje API bota. Konto nadal może sprawdzić pakiet i zgłosić aktywację. Aktywacja rozpoczyna nowy okres i odnawia limit. Przekierowanie w interfejsie nie zastępuje kontroli uprawnień w API.

Gość ma trzy udane porównania na dobę, kontrolowane przez plik sesji i skrót adresu połączenia. Samo usunięcie cookies nie odnawia limitu. Użytkownicy tej samej sieci mogą dzielić limit gości.

## 1. Podgląd strony bez konfiguracji

Wymagane Python 3.11+ i Node 22.

```bash
cd mobile
npm ci
npm run typecheck
npm test -- --runInBand
npx expo start --web
```

Bez zmiennych live działa oznaczony tryb demo. Wpisanie zapytania pokazuje oznaczony przykład ze wzoru, a zalogowanie otwiera demonstracyjny radar. Podgląd nie tworzy rzeczywistych kont i nie pobiera ofert z marketplace’ów.

## 2. Rzeczywista baza i pierwsze konto

Z głównego katalogu repozytorium:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-universal.txt
mkdir -p runtime
python -m universal_v2.hunter.bootstrap --auth-db runtime/auth.sqlite3 --username owner
cp examples/universal-hunter.example.json universal-hunter.local.json
cp PORTAL.env.example .env.portal.local
```

Na Windows aktywuj `.venv\Scripts\activate`. Bootstrap pyta o hasło i wypisuje rzeczywiste `owner_id`. Nie ma domyślnego hasła. **Konto właściciela utwórz przed pierwszym włączeniem portalu.** Przy istniejącej instalacji zachowaj jej bazę autoryzacji i użyj dotychczasowego konta.

W `universal-hunter.local.json` ustaw `owner_id`, rzeczywiste źródła i `database: "runtime/hunter.sqlite3"`. Wszystkie ścieżki względne konfiguracji skanera są liczone od pliku JSON. Konfigurację pięciu źródeł opisuje [UNIVERSAL_SETUP.md](UNIVERSAL_SETUP.md).

W `.env.portal.local` ustaw **absolutne** ścieżki do bazy kont, bazy radaru, plików poprzedniego API i eksportu web. Przykładowy plik zakłada instalację w `/srv/flipradar`; zmień te wartości na własne. Ustaw rzeczywistą domenę w `FLIP_PORTAL_ALLOWED_ORIGINS`, a `FLIP_PORTAL_OWNER_ID` na ID konta właściciela. Pierwsza migracja zachowuje dotychczasowe konta i zapisuje wybór właściciela. Zmiana samej zmiennej po migracji nie nadaje innej osobie uprawnień administratora.

```dotenv
FLIP_PORTAL_ENABLED=1
FLIP_PORTAL_OPEN_REGISTRATION=1
FLIP_PORTAL_COOKIE_SECURE=1
FLIP_PORTAL_ALLOWED_ORIGINS=https://twoja-domena.pl
```

Pliki `.env.portal.local`, bazy, sesje i katalog `runtime` są ignorowane przez Git.

## 3. Frontend live i wspólny adres HTTPS

```bash
cd mobile
cp portal.env.example .env
```

Ustaw `EXPO_PUBLIC_FLIP_API_URL` na dokładny publiczny adres tej samej strony, np. `https://twoja-domena.pl`, bez `/api`. W pliku przykładowym są już ustawione: live, web live, portal i źródło universal. Wartości `EXPO_PUBLIC_*` są publiczną konfiguracją kompilacji, więc nie umieszczaj w nich sekretów. Aplikacja nie pokazuje ich użytkownikowi.

```bash
npm ci
npm run typecheck
npx expo export --platform web
cd ..
python -m uvicorn universal_v2.portal.web:create_app --factory --env-file .env.portal.local --host 127.0.0.1 --port 8080
```

`FLIP_PORTAL_WEB_ROOT` musi wskazywać powstały katalog `mobile/dist`. Przed startem serwer sprawdza obecność eksportu. Ten sam proces obsługuje HTML, zasoby i `/api/*`; nie jest potrzebne szerokie CORS ani przekazywanie tokenów w URL. Ustaw własny reverse proxy HTTPS przed portem 8080, np. Caddy lub Nginx. Nie wystawiaj portu bazy danych. Zaufanie do nagłówków proxy ogranicz do konkretnego reverse proxy; fałszywy `X-Forwarded-For` nie powinien odnawiać limitu gości.

Po zmianie konfiguracji frontendu ponów eksport. Sama zmiana zmiennych w uruchomionym backendzie nie zmienia skompilowanego JavaScriptu. Dla wszystkich platform można użyć `npx expo export --platform all`.

Do lokalnego sprawdzenia rzeczywistych kont użyj lokalnego HTTPS, np. certyfikatu wystawionego przez `mkcert` dla `localhost` i portu 8443. Ustaw oba adresy konfiguracji na `https://localhost:8443`, ponów eksport i uruchom Uvicorn z `--ssl-certfile` i `--ssl-keyfile`. Zachowaj `FLIP_PORTAL_COOKIE_SECURE=1`. Flaga `FLIP_PORTAL_COOKIE_SECURE=0` jest wyłącznie dla lokalnych narzędzi HTTP; nie włącza HTTP w produkcyjnym eksporcie aplikacji.

## 4. Publiczna wyszukiwarka cen

Domyślnie `FLIP_PORTAL_PUBLIC_SEARCH_OWNER_ID` jest pusty: własne profile i wyniki pozostają prywatne. Jeżeli chcesz publikować porównania na stronie, wskaż jawnie konto z przygotowanym zbiorem ofert:

```dotenv
FLIP_PORTAL_PUBLIC_SEARCH_OWNER_ID=rzeczywiste-id-konta-ze-zbiorem-publicznym
FLIP_PORTAL_PUBLIC_DATA_IS_DEMO=0
```

Publiczny endpoint odczytuje do ośmiu już zebranych ofert pasujących do zapytania; nie wykonuje skanowania całego internetu na każde kliknięcie. Udostępnia tytuł, platformę, cenę, odnośnik i porównanie rynku. Nie ujawnia prywatnych kosztów, marży, ROI ani profili. Użytkownik żądania nie wybiera właściciela zbioru. Nie udostępniaj prywatnego zbioru, jeżeli nie chcesz publikować jego ofert.

Bez skonfigurowanego zbioru strona wyświetla przyjazny komunikat i nie zużywa wyszukiwania. Stała karta „Tak wygląda wynik” zawsze pozostaje oznaczonym przykładem.

Opcjonalna syntetyczna baza do sprawdzenia portalu:

```bash
python -m examples.generate_portal_demo --auth-db runtime/auth.sqlite3 --username owner --output runtime/portal-demo
```

Generator wykorzystuje istniejące konto; nie generuje hasła ani nie wysyła powiadomień. Wypisuje ścieżki i ID do lokalnej konfiguracji. Ustaw wskazane `FLIP_HUNTER_DB`, `FLIP_PORTAL_OWNER_ID`, `FLIP_PORTAL_PUBLIC_SEARCH_OWNER_ID` oraz **`FLIP_PORTAL_PUBLIC_DATA_IS_DEMO=1`**. Syntetycznych ofert nie należy przedstawiać jako rzeczywistych. Ustaw tę bazę również w konfiguracji kolektora albo korzystaj wyłącznie z wygenerowanego `runtime/portal-demo/config.json`.

## 5. Kolektor dla kont i powiadomienia

W portalu uruchamiaj jeden kolektor kont zamiast równoległego starego `hunter watch` dla tych samych profili:

```bash
python -m universal_v2.portal.collector --config universal-hunter.local.json --auth-db runtime/auth.sqlite3 --env-file .env.portal.local --once
python -m universal_v2.portal.collector --config universal-hunter.local.json --auth-db runtime/auth.sqlite3 --env-file .env.portal.local --network
```

Pierwsza komenda nie włącza pobierania sieciowego. Druga stale sprawdza źródła zgodnie z konfiguracją. Zatrzymaj ją przed zmianą konfiguracji i kolejnym uruchomieniem. Kolektor pomija wyłączone profile oraz konta bez dostępu, z wygasłym lub wstrzymanym pakietem. Start dostaje wyniki radaru bez tworzenia nowych alertów. Standard i Plus dostają własne alerty w ekranie powiadomień. Brak limitu na koncie nie oznacza braku limitów pobierania po stronie marketplace’ów.

`--deliver-owner` opcjonalnie włącza Telegram **wyłącznie właściciela konfiguracji**, według istniejących ustawień tokena i odbiorcy. Alerty innych kont nie są wysyłane do wspólnego czatu. Indywidualny Telegram, e-mail, push i płatności wymagają osobnych integracji; nie ma pozornej wysyłki. Każdy adapter live trzeba sprawdzić we własnym środowisku — ten kod nie potwierdza dostępu do wszystkich pięciu serwisów.

## 6. Zarządzanie dostępem

Zaloguj się kontem właściciela i otwórz `/account`. Nowi użytkownicy pojawią się w sekcji zarządzania dostępem. Wybierz pakiet i „Aktywuj”, następnie potwierdź konkretną zmianę. „Wstrzymaj” blokuje bota i unieważnia dotychczasowe sesje użytkownika. Samo ukrycie przycisku w UI nie daje uprawnień; endpoint wymaga roli właściciela.

Alternatywnie, na serwerze:

```bash
python -m universal_v2.portal.admin --database runtime/hunter.sqlite3 --auth-db runtime/auth.sqlite3 --owner-id ID_WLASCICIELA list
python -m universal_v2.portal.admin --database runtime/hunter.sqlite3 --auth-db runtime/auth.sqlite3 --owner-id ID_WLASCICIELA activate --user-id ID_KONTA --plan STANDARD
python -m universal_v2.portal.admin --database runtime/hunter.sqlite3 --auth-db runtime/auth.sqlite3 --owner-id ID_WLASCICIELA disable --user-id ID_KONTA
```

Hasła korzystają z dotychczasowego PBKDF2 z losową solą. Przeglądarka utrzymuje sesję w cookie `Secure`, `HttpOnly`, `SameSite=Lax`; tokeny nie trafiają do `localStorage`. Wylogowanie unieważnia również wznowione karty tej przeglądarki. Native korzysta z dotychczasowej rotacji tokenów i SecureStore. Publiczna rejestracja nie przyjmuje roli ani pakietu.

Kod nie zawiera weryfikacji e-mail, samoobsługowego resetu hasła ani obsługi faktur. Informacje w stopce opisują zaimplementowane działanie; przed sprzedażą uzupełnij dane operatora i właściwe warunki świadczenia usługi.

## 7. Usługi i zgodność z dotychczasowym API

Przykłady w `ops/systemd/flipradar-portal-*.service.example` zakładają użytkownika `flipradar`, projekt `/srv/flipradar`, konfigurację `/etc/flipradar/portal.env` i `/etc/flipradar/hunter.json`. Dostosuj ścieżki i prawa dostępu przed instalacją. Pliki nie instalują się automatycznie ani nie zmieniają istniejących usług.

Portal uruchamia się tylko przy `FLIP_PORTAL_ENABLED=1`. Bez tej flagi pozostają dotychczasowe kontrakty i sposób działania API. Nowe trasy `/api/v1/portal/*` i `/api/v1/public/*` są dodatkiem. Włączony portal narzuca uprawnienia na endpointy bota; nowe konta nie mogą czytać starego globalnego radaru `/api/v1/radar` i `/api/v1/listings`. Korzystają z radaru `/api/v1/universal/mobile-radar` przypisanego do ich konta.

Przy istniejącym wdrożeniu najpierw zrób kopię baz i ustaw osobną bazę hunter. Baza `auth.sqlite3` pozostaje bazą kont, a dane pakietów i limitów trafiają do tabel `portal_*` w bazie hunter. Nie wskazuj bazy starego skanera jako `FLIP_HUNTER_DB`.

## Weryfikacja

```bash
pip install -r requirements-universal-test.txt
python -m pytest tests/test_hunter_*.py tests/test_portal_*.py -q
ruff check --isolated --select E4,E7,E9,F,I universal_v2/hunter universal_v2/portal examples/generate_portal_demo.py tests/test_portal_*.py
cd mobile
npm run typecheck
npm test -- --runInBand
npx expo export --platform all
```

Pełna regresja starego backendu wymaga jego zależności z `requirements.txt` i `backend/requirements.txt`. Wyniki wykonanej walidacji znajdują się w [PORTAL_VALIDATION.md](PORTAL_VALIDATION.md).
