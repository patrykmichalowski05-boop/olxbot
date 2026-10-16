# Uruchomienie uniwersalnego FlipRadar

## 1. Sprawdź paczkę offline

Wymagane Python 3.11+ i Node 22 dla aplikacji mobilnej. Poniższe polecenia wykonuj z głównego katalogu repozytorium.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-universal-test.txt
python -m pytest tests/test_hunter_*.py -q
python -m examples.generate_hunter_demo
python -m universal_v2.hunter --config runtime/demo/config.json validate
python -m universal_v2.hunter --config runtime/demo/config.json scan
python -m universal_v2.hunter --config runtime/demo/config.json scan
```

Demo używa 30 syntetycznych ofert, pięciu źródeł i pięciu profili. Pierwszy skan kolejkuje 5 alertów; drugi nie tworzy duplikatów. Dane i SQLite trafiają do ignorowanego katalogu `runtime/demo`. Żaden z tych kroków nie wysyła Telegrama ani nie łączy się z marketplace’ami.

## 2. Konto API i konfiguracja

Jeżeli masz już działające konto aplikacji, zachowaj bazę autoryzacji. Odczytaj `user_id` z istniejącego `/api/v1/me` i użyj go jako `owner_id` konfiguracji skanera. Nowy moduł korzysta z istniejących tokenów Bearer.

Dla nowej, lokalnej instalacji:

```bash
mkdir -p runtime
python -m universal_v2.hunter.bootstrap --auth-db runtime/auth.sqlite3 --username owner
cp examples/universal-hunter.example.json universal-hunter.local.json
```

Kreator pyta o hasło przez bezpieczne wejście terminala i wypisuje `owner_id`. Nie twórz nowego właściciela w używanej bazie — bootstrap celowo pozwala utworzyć tylko pierwsze konto.

W `universal-hunter.local.json` ustaw:

- `owner_id` na rzeczywiste ID konta;
- `database` na `runtime/hunter.sqlite3` — ścieżki względne liczone są od katalogu pliku konfiguracji;
- źródła i interesujące modele; usuń profile, których nie chcesz używać;
- rzeczywiste koszty, prowizje i margines bezpieczeństwa.

Plik przykładowy jest w `examples/`, więc jego domyślna baza to `../runtime/hunter.sqlite3`. Po skopiowaniu do katalogu głównego zmień ją na `runtime/hunter.sqlite3`.

```bash
python -m universal_v2.hunter --config universal-hunter.local.json validate
```

`validate` sprawdza strukturę i progi, nie testuje logowania ani dostępności stron. Profile są dodawane do bazy przy pierwszym uruchomieniu. Kolejne uruchomienia zachowują zmiany z aplikacji. Flaga `--sync-config` jawnie nadpisuje profile o tych samych ID danymi z pliku; nie usuwa pozostałych profili z bazy.

## 3. Źródła

Każda platforma ma jeden skonfigurowany adapter. Profile mogą wybierać dowolny podzbiór platform.

| Tryb | Działanie | Wymagania |
| --- | --- | --- |
| `html` | Publiczny HTML, JSON-LD i widoczne karty | Dostępna strona i dozwolony odczyt w robots.txt |
| `browser` | Widoczna strona w lokalnym Playwright | Zainstalowany Chromium; przy Facebooku własny plik sesji |
| `json` | Plik z danymi użytkownika lub dostawcy | Aktualizowany plik zgodny ze schematem `Offer` |

| Platforma | Tryb w przykładzie | Faktyczny stan walidacji |
| --- | --- | --- |
| OLX | HTML | Parser i obsługa blokad przetestowane na fixture’ach; live wymaga sprawdzenia |
| Facebook Marketplace | Przeglądarka + sesja | Parser przetestowany; nie logowano się na konto użytkownika |
| Allegro Lokalnie | HTML | Publiczna ścieżka wyszukiwania, parser przetestowany; brak testu live |
| Otomoto | Przeglądarka | Parser przetestowany; URL filtrów trzeba sprawdzić w aktualnym serwisie |
| Vinted | Przeglądarka | Parser przetestowany; dostęp i aktualny układ strony wymagają sprawdzenia |

Instalacja przeglądarki:

```bash
pip install -r requirements-universal-browser.txt
python -m playwright install chromium
```

Na serwerze Linux mogą być potrzebne zależności systemowe Chromium; zgodnie z instalatorem Playwright można użyć `python -m playwright install --with-deps chromium`.

Dla Facebooka adapter odczytuje ścieżkę z `FLIP_FACEBOOK_STORAGE_STATE`, wskazaną przez `storage_state_env` w konfiguracji. Utwórz własną sesję ręcznie w lokalnej przeglądarce Playwright, jeśli platforma na to pozwala:

```bash
python -m playwright codegen --save-storage=runtime/facebook.storage-state.json https://www.facebook.com/marketplace/
export FLIP_FACEBOOK_STORAGE_STATE="$PWD/runtime/facebook.storage-state.json"
```

Bot nie wpisuje danych logowania, nie rozwiązuje CAPTCHA ani nie obchodzi blokad. Sesja jest lokalnym sekretem i nie powinna trafić do Gita. Brak dostępu daje stan źródła i ponowienie z rosnącym odstępem, nie pusty sukces. Jeżeli robots.txt odmawia dostępu, użyj własnego/dostarczonego feedu `json`; tryb przeglądarki także respektuje odmowę.

W profilu można podać `source_urls`, np. skopiowany z serwisu URL wyszukiwania konkretnego auta. Każdy adres musi używać HTTPS i należeć do właściwej platformy. Nie można podać adresu dowolnego serwera lub pliku.

Adapter pobiera ograniczoną listę wyników; `max_items` wynosi domyślnie 100 (maksymalnie 300). Nie ma pełnego indeksowania wszystkich stron, miast i krajów. Przeglądarka wykonuje dwa przewinięcia strony. Dla dużych zbiorów użyj feedu albo kilku precyzyjnych profili. `json` przyjmuje maksymalnie 5000 wierszy i 6 MB, a `max_items` również ogranicza wynik adaptera.

Przykład importu:

```json
{
  "items": [{
    "platform": "OLX", "external_id": "ID123",
    "title": "RTX 4070 12GB", "price_minor": 120000,
    "url": "https://www.olx.pl/d/oferta/karta-ID123.html",
    "condition": "USED", "attributes": {"vram_gb": 12},
    "observed_at": "2026-10-15T12:00:00+00:00"
  }]
}
```

Źródło w konfiguracji: `{"platform":"OLX","mode":"json","feed_path":"runtime/olx.json"}`. Feed może zawierać także droższe oferty porównawcze. Zaktualizuj jego dane i daty przy kolejnych odczytach. Bez `observed_at` używany jest czas importu — nie dowodzi to aktywności ogłoszenia w serwisie. Brak oferty na ograniczonej liście wyników nie oznacza jej sprzedaży ani usunięcia; jawne `status: "REMOVED"` unieważnia alert. `SOLD_VERIFIED` przyjmowane jest tylko z dostarczonym `sale_evidence`; dostawca odpowiada za prawdziwość dowodu.

## 4. Powiadomienia Telegram

Utwórz lokalny, ignorowany `.env`, np. na podstawie `.env.example`, i wpisz własne `TELEGRAM_BOT_TOKEN` oraz `TELEGRAM_CHAT_ID`. Domyślne nazwy można zmienić przez `telegram_token_env` i `telegram_chat_env`; wartości tokenów nie trafiają do konfiguracji profili ani bazy.

```bash
python -m universal_v2.hunter --config universal-hunter.local.json --network scan
python -m universal_v2.hunter --config universal-hunter.local.json status
python -m universal_v2.hunter --config universal-hunter.local.json --env-file .env --deliver dispatch
python -m universal_v2.hunter --config universal-hunter.local.json --env-file .env --network --deliver watch
```

`--network` włącza skonfigurowane źródła sieciowe. `--deliver` włącza rzeczywistą wysyłkę. Bez tokena i odbiorcy kolejka pozostaje nietknięta, a status wysyłki to `NOT_CONFIGURED`.

Pierwsze udane pobranie danej platformy/profilu tworzy cichą bazę odniesienia (`notify_initial=false`). Potem alert dotyczący tego samego przedmiotu powstaje przy nowej kwalifikującej się ofercie albo niższej cenie. Drobna zmiana opisu nie powoduje ponownego alertu przy tej samej cenie. Włączenie `notify_initial=true` pozwala alarmować już przy pierwszym odczycie.

Kolejka jest trwała, ma dzierżawy dla workerów, do 8 prób, opóźnienia po 429 i termin ważności 6 godzin. Wycofana oferta, zmiana ceny, wyłączony profil i utrata kwalifikacji unieważniają oczekujący alert. Przed wysłaniem bot weryfikuje lokalną obserwację; nie sprawdza osobno strony oferty w tym momencie. Po upływie 6 godzin alert wygasa. Po poprawieniu konfiguracji/dostępu stan `FAILED` można jawnie ponowić poleceniem `python -m universal_v2.hunter --config universal-hunter.local.json retry-failed`, a następnie `dispatch --deliver` (flagi podawaj przed poleceniem). Ponowienie obejmuje tylko niewygasłe alerty danego właściciela; nie ma nieskończonego ponawiania.

Dokładnie jedna zewnętrzna dostawa nie jest gwarantowana: awaria po przyjęciu wiadomości przez Telegram, ale przed zapisem potwierdzenia w SQLite, może spowodować ponowienie. To ograniczenie zewnętrznej wysyłki, niezależne od deduplikacji nowych ofert.

`watch` odczekuje `interval_seconds` po całym cyklu; rzeczywisty czas cyklu zależy też od platform i limitów. Uruchamiaj jeden kolektor dla danej konfiguracji. Można użyć osobnego workera `dispatch`. Kody zakończenia: 0 sukces, 1 brak udanego źródła w `scan`, 2 błąd konfiguracji, 3 niedostępna baza, 130 przerwanie.

## 5. API i aplikacja Expo

Istniejąca usługa bez `FLIP_HUNTER_DB` zachowuje poprzednie źródła i kontrakty. Aby podłączyć nowy radar, wskaż bazę **tego samego kolektora**:

```bash
export FLIP_API_AUTH_DB="$PWD/runtime/auth.sqlite3"
export FLIP_API_DATA_ROOT="$PWD/runtime"
export FLIP_UNIVERSAL_DEV_DIR="$PWD/runtime"
export FLIP_HUNTER_DB="$PWD/runtime/hunter.sqlite3"
python -m uvicorn universal_v2.mobile_bridge:create_app --factory --host 127.0.0.1 --port 8000
```

Przy istniejącej instalacji `FLIP_API_AUTH_DB` i `FLIP_API_DATA_ROOT` nadal wskazują jej dotychczasowe dane. Nowa baza musi być osobnym plikiem; moduł odrzuca próbę wykorzystania obcej bazy. Nie włączaj jednocześnie `FLIPRADAR_READ_LEGACY_SNAPSHOTS=1`. Zmiana źródła radaru zmienia przestrzeń identyfikatorów snapshotów — przed migracją przejrzyj zapisane odnośniki watchlisty.

Dostęp z urządzenia zapewnij przez własny reverse proxy HTTPS do lokalnego API. Proces nie zmienia firewalla ani konfiguracji serwera. Dla live na web potrzebna jest też konfiguracja tego samego origin lub właściwej polityki CORS na reverse proxy; nie rozszerzano istniejącej polityki API.

W `mobile/.env` ustaw:

```dotenv
EXPO_PUBLIC_FLIP_API_URL=https://twoj-host
EXPO_PUBLIC_FLIP_RADAR_SOURCE=universal
EXPO_PUBLIC_FLIP_APP_MODE=live
```

Dla live na web ustaw również `EXPO_PUBLIC_FLIP_WEB_LIVE=1`. Zmienne te służą konfiguracji, a nie komunikatom dla użytkownika.

```bash
cd mobile
npm ci
npm run typecheck
npm test -- --runInBand
npx expo start
```

W aplikacji otwórz **Ustawienia → Moje wyszukiwania i alerty**. Ustaw model z wariantem, platformy, kategorię, budżet, koszty i minimalny ROI. Można wstrzymywać zapisane profile. Edycja zaawansowanych cech i pełnych profili jest dostępna przez API/konfigurację. Stary backend bez tej funkcji pokazuje przyjazny stan niedostępności, bez surowego błędu HTTP.

Nowe endpointy używają tych samych tokenów:

| Metoda | Endpoint | Zastosowanie |
| --- | --- | --- |
| GET | `/api/v1/universal/searches` | Profile zalogowanego właściciela |
| PUT | `/api/v1/universal/searches/{id}` | Utworzenie/zastąpienie pełnego profilu |
| DELETE | `/api/v1/universal/searches/{id}` | Usunięcie i anulowanie oczekujących alertów |
| GET | `/api/v1/universal/source-health` | Stan źródeł i liczby stanów kolejki |
| GET | `/api/v1/universal/mobile-radar` | Istniejący format listy radaru |
| GET | `/api/v1/universal/mobile-radar/{snapshot_id}` | Istniejący format szczegółów |

Limit to 100 profili na konto. Usługa skanera przetwarza wyłącznie `owner_id` ze swojej lokalnej konfiguracji, także dla profili utworzonych przez aplikację. Sam zapis profilu nie uruchamia automatycznie procesu na serwerze. To obecnie rozwiązanie dla właściciela instalacji; zarządzanie wieloma użytkownikami wymaga osobnego provisioningu i przypisania odbiorców.

## 6. Koszty, warianty i wycena

Kwoty konfiguracji/bazy podawane są w **groszach**. `150000` = 1500 zł. `min_roi_bps=2000` = 20%; `sale_fee_bps=600` = 6%. Formularz aplikacji przyjmuje złote i procenty, po czym wykonuje konwersję.

Wynik = odsprzedaż − zakup − wysyłka − naprawy − dojazd − inne koszty − prowizja od odsprzedaży − rezerwa od zakupu. ROI = wynik / całkowity zaangażowany kapitał. Limit zakupu spełnia jednocześnie minimalny zysk i ROI. Podatki nie są obliczane.

Do wyceny potrzeba domyślnie 5 porównań (minimum konfigurowalne 3). Kandydat nie jest własnym porównaniem. Gdy znane jest ID sprzedawcy, jeden sprzedawca daje jeden punkt odniesienia. Ceny ofertowe dostają konserwatywną korektę i niską pewność; nie są dowodem sprzedaży. Brak dostatecznej liczby porównań, duży rozrzut, stara data albo niepełny wariant daje brak wyceny.

Rozpoznawanie automatyczne obejmuje rodziny iPhone/Galaxy oraz GPU RTX/GTX/RX. Porównania telefonów wymagają modelu i pamięci; GPU modelu i VRAM; PC CPU/GPU/RAM/dysków. Auta wymagają roku, pasma przebiegu, silnika i skrzyni, a przykładowy profil dodaje generację i nadwozie. Moda wymaga kodu produktu i rozmiaru; autentyczność nadal wymaga weryfikacji. Pozostałe produkty potrzebują jawnego `variant_keys`, np. `kit` dla narzędzi, oraz tych cech w danych oferty. Nie zgaduj brakujących wartości.

`purpose: "cheap"` obserwuje dowolne przedmioty pasujące do tytułu i ustawionego limitu. Jeżeli nie ma porównań, alert podaje dobrą cenę według Twojego progu, bez wymyślonego ROI. Tryb `flip` wymaga wiarygodnego zestawu porównań i wszystkich progów. W żadnym trybie bot nie kupuje przedmiotu automatycznie.
