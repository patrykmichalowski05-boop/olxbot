# FlipRadar — radar okazji i potencjalnego zysku

Repozytorium zawiera skaner PC OLX/Facebook, panel webowy, aplikację Expo i nowy, odseparowany moduł uniwersalny.

Nowy moduł `universal_v2/hunter` obsługuje profile wyszukiwania dla **OLX, Facebook Marketplace, Allegro Lokalnie, Otomoto i Vinted**. Łączy import/pobieranie ofert, rozpoznawanie wariantów, porównania rynku, koszty i trwałą kolejkę Telegram. Aplikacja mobilna ma ekran **Ustawienia → Moje wyszukiwania i alerty**.

**Status:** logika i formaty danych są przetestowane lokalnie. Adaptery stron wymagają sprawdzenia dostępu w środowisku użytkownika; testy nie potwierdzają działającego pobierania live ze wszystkich pięciu serwisów. Nie ma gwarancji pokrycia całego rynku ani gwarantowanego zarobku. Brak danych porównawczych oznacza brak wyceny.

## Uruchomienie bez internetu i bez kluczy

Python 3.11+; polecenia z katalogu głównego repozytorium:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-universal.txt
python -m examples.generate_hunter_demo
python -m universal_v2.hunter --config runtime/demo/config.json scan
python -m universal_v2.hunter --config runtime/demo/config.json scan
```

Generator tworzy wyłącznie syntetyczne oferty. Pierwszy skan zapisuje 5 alertów w kolejce, drugi 0 nowych. Te polecenia nie wysyłają wiadomości. Na Windows aktywuj środowisko przez `.venv\Scripts\activate`.

## Dokumentacja

- [Instalacja, Telegram, pięć platform, API i aplikacja](docs/UNIVERSAL_SETUP.md)
- [Analiza kodu, architektura i ograniczenia](docs/UNIVERSAL_AUDIT.md)
- [Konfiguracja pięciu przykładowych wyszukiwań](examples/universal-hunter.example.json)
- [Aplikacja mobilna](mobile/README.md)
- [Dotychczasowy panel PC](README_GUI_V2.md)

Stary skaner, wycena PC i PostgreSQL dla flipów pozostają osobnymi modułami. Nowego radaru nie włącza się automatycznie w istniejącej usłudze API.
