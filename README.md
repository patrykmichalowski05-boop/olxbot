# FlipRadar — bot i nowe GUI

Repozytorium zawiera skanery OLX / Facebook, panel Flask oraz kilka wcześniejszych paczek aplikacji. Nowy interfejs korzystający z obecnego logowania i danych bota znajduje się w **`active/flipradar-v12/`**.

| Część | Lokalizacja |
| --- | --- |
| Aktualne źródła GUI Expo / React Native / Expo Router / TypeScript | `active/flipradar-v12/mobile/` |
| Gotowy eksport webowy, fonty i ikony | `active/flipradar-v12/dist/` |
| Połączenie GUI z istniejącą sesją i prywatnymi radarami | `active/flipradar-v12/v12_bridge.py` |
| Odczyt globalnego radaru i magazynu administratora | `active/flipradar-v12/flipradar_legacy_bridge.py` |
| Dotychczasowy serwer i narzędzia | `flip_v2_overlay_dev.py`, `webapp_v2.py`, `app_v2/` |
| Skanery i wycena | istniejące moduły w katalogu głównym oraz `facebook/` |

**Uruchomienie i zakres integracji:** [active/flipradar-v12/INTEGRATION.md](active/flipradar-v12/INTEGRATION.md).

Nowe GUI używa kont V10 i istniejącej sesji Flask. Zwykłe konto widzi własne wyszukiwania, oferty oraz powiadomienia. Konto głównego administratora może czytać globalne wyniki bota, a administratorzy — magazyn. Dotychczasowe centrum narzędzi pozostaje dostępne pod `/centrum?tab=dashboard`.

Pełna instalacja serwerowa nie jest jeszcze odtwarzalna z samego klonu: `flip_v2_overlay_dev.py` importuje 13 modułów V1–V11 nieobecnych w repozytorium. Diagnostyka poniżej podaje ich nazwy, bez importowania serwera i otwierania baz:

```bash
python3 active/flipradar-v12/runtime_check.py
```

Brakujących modułów kont i uprawnień nie zastępuje drugi system logowania. Integrację należy uruchomić z ich rzeczywistymi kopiami z obecnej instalacji. Instrukcja wyjaśnia także różnicę między podglądem a trybem live.

Starsze katalogi `active/flipradar-ui/current/`, `active/flipradar-portal/source/` i `active/flipradar-universal/app/` zachowano jako wcześniejsze warianty. Nie należy uruchamiać ich jako drugiego backendu dla aktualnych kont V10.
