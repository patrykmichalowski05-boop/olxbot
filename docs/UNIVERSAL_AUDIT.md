# Analiza repozytorium i zakres przebudowy

Analiza wykonana 2026-10-15 dla `patrykmichalowski05-boop/olxbot`. Punktem wyjścia jest `feature/flipradar-mobile-premium-test`, commit `4289ae2b113655f9e57b743eeb3365610adeba85`. Gałąź `main` nie zawierała tego samego zestawu API i aplikacji mobilnej, więc przygotowanie zmian tylko względem `main` pomijałoby aktualny FlipRadar.

Przejrzano strukturę całego repozytorium i wykonano inwentaryzację składni wszystkich 332 zastanych modułów Python. Szczegółowy przegląd objął główny tor skanowania, parsery FB, wycenę PC, Telegram, `app_v2`, zapisane wyszukiwania, `universal_v2`, API mobilne, autoryzację, PostgreSQL oraz klienta Expo i testy. Kopie zapasowe/wersje etapowe rozpoznano jako osobne, nieaktywne warianty; nie przepisywano ich ani nie usuwano.

## Najważniejsze ustalenia

| Obszar | Zastany problem | Zmiana |
| --- | --- | --- |
| `scanner.py`, `fast_scanner.py` | Zapytania i filtry nastawione na PC, nie uniwersalne produkty | Nowy, równoległy runtime, bez przepisywania działającego skanera PC |
| `app_v2/saved_searches_v1.py` | Kategorie sprzętowe, OLX/FB i ścieżki związane z instalacją dev | Profile w osobnej SQLite, 5 platform, dowolna nazwana kategoria i cechy |
| `universal_v2` | Prototypy, wyłączone źródła, brak spójnej automatycznej ścieżki | Pobieranie/import → obserwacja → dopasowanie → wycena → kolejka → dostawa |
| Porównania | Sam tytuł i cena nie dowodzą zgodności wariantu | Klucze wariantu, stan przedmiotu, świeżość i minimum próbek |
| Zysk | Potrzeba uwzględniania kosztów i dwóch progów naraz | Kwoty całkowite w groszach, ROI od całego kapitału, limit zakupu spełniający zysk i ROI |
| Powiadomienia | Duplikaty i utrata alertu między zapisem a wysyłką | Transakcja SQLite obejmująca wynik i outbox, unikalne zdarzenie ceny, dzierżawy i retry |
| Błędy platform | Odmowa odczytu nie może znaczyć „0 ofert” | Osobne stany login/blokada/429/zmieniony parser/nieprawidłowy feed |
| API i mobile | Potrzebny wspólny radar bez zerwania dotychczasowych endpointów | Opcjonalne `FLIP_HUNTER_DB`, ten sam format listy/szczegółów, nowe uwierzytelnione CRUD |
| Interfejs | Wyszukiwania wymagałyby ręcznego JSON | Ekran modeli, platform, kategorii, budżetu, kosztów, ROI i pauzy |
| Opisy analizy | Reguł i porównań nie należy podpisywać jako AI | Rozróżnione „Analiza rynku” i rzeczywiste istniejące podsumowanie AI |
| `ai_analyzer.py`, `spec_recovery.py` | OpenAI uruchamiane podczas importu, blokada testów bez klucza | Leniwe tworzenie klienta; algorytm i format wyników bez zmian |
| Starsze testy | Nieistniejący `mobile/src/api.ts` i nieaktualne oczekiwanie po replay tokena | Wskazanie bieżącego klienta; zachowane unieważnianie całej rodziny tokenów |

## Granice integracji

W tym środowisku **nie potwierdzono pobierania live** z pięciu platform, nie logowano się do kont marketplace i nie wysyłano prawdziwych wiadomości Telegram. Testy adapterów używają kontrolowanego HTML/JSON, a testy transportu atrap odpowiedzi HTTP. To weryfikuje kod i obsługę błędów, nie gwarantuje aktualności każdego selektora na stronie serwisu.

Nie ma publicznego wspólnego API, które ten kod mógłby automatycznie traktować jako pełny katalog wszystkich pięciu serwisów. Sprawdzone oficjalne dokumentacje:

- [OLX Partner API](https://developer.olx.pl/api/doc) — integracje partnerów i ogłoszeń; nie należy z góry zakładać uprawnienia do pełnego wyszukiwania rynku.
- [Allegro — lista metod](https://developer.allegro.pl/tutorials/lista-metod-rest-api-allegro-yPyaj0wG3C4) — opis `/offers/listing` informuje o niedostępnym zasobie i wstrzymanej weryfikacji. Adapter Allegro Lokalnie korzysta z publicznej strony, nie z tego endpointu Allegro.
- [Vinted Pro Integrations](https://pro-docs.svc.vinted.com/) — API zarządzania pozycjami/integracją sprzedawcy; `GET /api/v1/items` opisuje pozycje utworzone w VPI, nie ogólne wyszukiwanie konsumenckiego katalogu.
- [Telegram Bot API](https://core.telegram.org/bots/api) — `sendMessage`, format HTML i parametry ponowień po 429.

Przeglądarka jest opcjonalnym sposobem odczytu widocznej strony, a nie obejściem zasad dostępu. Brak uprawnień, CAPTCHA, robots.txt lub nieaktualny DOM są rzeczywistymi blokadami i wymagają zgodnego źródła danych albo aktualizacji adaptera. Pełne pokrycie wszystkich ogłoszeń, wszystkich wariantów produktów i cen zakończonych transakcji nie jest zaimplementowane.

## Architektura

- `models.py`: walidacja profilu, cech, kwot, źródeł i adresów; bez kwot zmiennoprzecinkowych w obliczeniach.
- `matching.py`: słowa wymagane/wykluczone, cechy, rodziny sprzętu, warianty i ryzyka.
- `parsers.py`: JSON-LD oraz karty pięciu platform; brak wykonywania znalezionego JavaScriptu.
- `sources.py`: HTML, opcjonalny Playwright, import JSON, limity, robots.txt, odstępy i jawne błędy.
- `pricing.py`: selekcja porównań, dolny kwartyl, odrzucanie odstających cen, ostrożna prognoza i progi.
- `store.py`: jedna SQLite dla ofert, rewizji, wyników, profili, stanu źródeł i kolejki.
- `runner.py`: koordynacja pobrania i grupowania wariantów, wycena po zebraniu obserwacji, cichy pierwszy odczyt per platforma/profil.
- `notify.py`: odbiorca z lokalnego środowiska, bezpieczne formatowanie, retry/429 i brak wycieku tokena w błędzie transportu.
- `api.py`: profile i stan źródeł przypisane do istniejącego uwierzytelnionego właściciela.
- `__main__.py`, `bootstrap.py`: uruchomienie jednorazowe, stały proces, diagnostyka kolejki i lokalny bootstrap konta.

Przeliczenia wewnętrzne są w groszach i punktach bazowych. Wyłącznie istniejący kontrakt `valuation.quick_sale`, `profit`, `total_cost` w API mobilnym korzysta ze złotych; dodane `roi_bps` zachowuje dokładną wartość ROI po kosztach. Deterministyczne podsumowanie nie wymaga OpenAI.

Kandydat nie wycenia sam siebie. Sprzedaż potwierdzona wymaga jawnego dowodu z dostawcy; jej rzetelności nie dowodzi sam tekst pola. Gdy nie ma minimalnej liczby takich sprzedaży, moduł używa oddzielnie aktywnych cen ofertowych, z korektą i niską pewnością. Nie miesza małej próbki sprzedaży z cenami ofertowymi, by sztucznie dobić minimum.

## Zachowane zachowania

Bez `FLIP_HUNTER_DB` wcześniejsze źródło radaru i endpointy pozostają aktywne. `/api/v1/radar`, autoryzacja, refresh/logout, stare manual/watchlist oraz PostgreSQL nie zostały zastąpione nową bazą. Nowy moduł nie zapisuje w bazach skanera PC ani w księdze rzeczywistych flipów. Nie zmienia istniejących zadań systemd, nie publikuje repozytorium i nie wykonuje zakupów.

Zmiana źródła radaru jest osobną decyzją konfiguracyjną. Wcześniejsze `snap-{id}` na watchliście mogą odnosić się do poprzedniej bazy, dlatego migracja zapisanych odnośników wymaga sprawdzenia. Rozszerzenie jest przeznaczone dla właściciela obecnej instalacji; nie jest gotową usługą SaaS z samodzielną rejestracją i płatnościami.

## Walidacja i dalsze ograniczenia

Szczegóły konkretnych uruchomień i wyniki końcowe znajdują się w `VALIDATION.md` w paczce oraz w raporcie testów. Testy obejmują m.in. niezgodne modele i pamięć, uszkodzenia, niepełne ceny, waluty, koszty, progi ROI, stare porównania, braki danych, parsery pięciu platform, blokady źródeł, transakcję wyniku/alertu, restart, cichy start, spadki cen, równoległe claimy, stare dzierżawy i izolację kont.

Należy zweryfikować na własnym środowisku: aktualny DOM i filtrowanie stron, uprawniony dostęp/sesje, rzeczywisty odbiorca Telegram, rozkład kosztów oraz dane porównawcze. Osobno pozostają testy fizycznych urządzeń iOS/Android i integracja PostgreSQL wymagająca dostępnej bazy. Dotychczasowy moduł ręcznej analizy nie został podmieniony na automatyczne pobieranie dowolnego linku; zachowuje istniejący kontrakt.
