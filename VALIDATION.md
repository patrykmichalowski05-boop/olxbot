# Walidacja — FlipRadar Universal

Data: 2026-10-15. Baza zmian: `4289ae2b113655f9e57b743eeb3365610adeba85`, gałąź `feature/flipradar-mobile-premium-test`.

| Sprawdzenie | Wynik |
| --- | --- |
| Pełna regresja `python -m pytest tests -q -rs --disable-warnings` | **425 passed, 8 skipped, 53 subtests passed** |
| Nowy moduł, czyste środowisko z `requirements-universal-test.txt` | **93 passed** |
| Mobilne `npm test -- --runInBand` | **32 passed, 8 suites** |
| `mobile`: `npm run typecheck` | **PASS** |
| `npx expo export --platform all` | **PASS: Android, iOS, web; 21 tras, w tym `/searches`** |
| Ruff dla nowego modułu, przykładów i testów: `--isolated --select E4,E7,E9,F,I` | **PASS** |
| Parsowanie AST wszystkich modułów Python po zmianach | **352 moduły, 0 błędów składni** |
| `git diff --check` | **PASS** |
| CLI offline: generator → validate → scan → ponowny scan | **5 nowych alertów, następnie 0 duplikatów** |

Nowy moduł sprawdzono w świeżym środowisku Python 3.12 z samymi zależnościami `requirements-universal-test.txt`; nie wymaga OpenAI, Flask ani PostgreSQL. Pełna regresja starszego kodu dodatkowo wymaga zależności z `backend/requirements.txt`, Flask, Playwright i OpenAI. W testach nie wykorzystano rzeczywistych kluczy API.

Osiem pominiętych testów wymaga jednorazowej bazy PostgreSQL (`tests/test_backend_pg_*.py`). Nie zaliczono ich jako poprawnie wykonanych. Istniejący workflow GitHub ma osobny serwis PostgreSQL do tych testów; nowy workflow dodaje niezależne testy modułu uniwersalnego i demo bez sieci.

W czystym środowisku występuje pojedyncze ostrzeżenie deprecacyjne Starlette dotyczące klienta testowego httpx; nie jest to błąd aplikacji ani wyłączenie testów. Nie aktualizowano w związku z nim istniejących kontraktów autoryzacji.

## Co rzeczywiście przetestowano

- Ceny w groszach, separatory, błędne/niepełne kwoty, waluty, koszty i limit zakupu spełniający ROI oraz zysk.
- Odróżnianie RTX/Ti/Super, modelu i pamięci telefonu, PC vs GPU, cech aut i brakujących wariantów; ryzyka w tytule/opisie.
- Brak wyceny przy zbyt małej próbce, starych/futurystycznych datach i niezgodnym modelu; odrębne ceny ofertowe i potwierdzone sprzedaże.
- HTML i JSON-LD dla pięciu platform; blokady, login, zmieniony parser, robots.txt, 429, obcy redirect i błędny feed.
- Atomowy zapis wyniku i outboxa, rollback błędu bazy, restart, deduplikacja, cichy pierwszy odczyt, spadki cen, dwa workery, stare dzierżawy, pauza i anulowanie nieaktualnego alertu.
- Trwałe ponowienia, respektowanie limitu Telegrama także dla nowych alertów, jawne ponowienie błędów końcowych i brak ujawnienia tokena w wyjątku transportu.
- Wymóg Bearer, izolacja właścicieli, CRUD profili, stronicowanie i istniejący format radaru/szczegółów.
- Konwersja kwot i ROI w mobile, rozróżnianie analizy regułowej od AI, zachowanie istniejących pól klienta.

## Czego te wyniki nie potwierdzają

Nie wykonano testu pobierania live z kont marketplace, rzeczywistego wysłania Telegrama, automatycznego rozpoznania dowolnego przedmiotu na rynku ani testów na fizycznych urządzeniach. Eksport Expo potwierdza kompilację i generowanie pakietów, nie pełne zachowanie aplikacji na urządzeniu. Nie uruchamiano usług produkcyjnych, migracji PostgreSQL, publikacji ani wdrożenia repozytorium.

Instrukcja konfiguracji i ograniczenia: [docs/UNIVERSAL_SETUP.md](docs/UNIVERSAL_SETUP.md), [docs/UNIVERSAL_AUDIT.md](docs/UNIVERSAL_AUDIT.md).
