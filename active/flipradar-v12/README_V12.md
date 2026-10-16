# FlipRadar V12 — ORYGINALNY React/Expo UI z przesłanego ZIP-a

## Czym różni się od nieudanego V11?

V11 przepisywał część projektu na szablony Flask. V12 **buduje i uruchamia rzeczywisty projekt `source/mobile` (Expo Router + React)** z dokładnie tej paczki, którą użytkownik zaakceptował na porcie 8093. Wszystkie oryginalne style i React-owe ekrany bota pochodzą z tego źródła. Zmienione zostały wyłącznie ścieżki do API, rejestracja z e-mailem, opcja usunięcia konta i widoczne ostrzeżenie przy nieobsługiwanych filtrach.

Nie jest to drugi system kont. Backend to **Flask V10/V11 + SQLite V9**. Interfejs łączy się z nim przez osobny moduł `v12_bridge.py`, oparty na oryginalnej sesji serwera. Nie ma demonstracyjnych ofert ani migracji kont.

## Aktualny zakres funkcjonalny

Działa w adapterze LIVE:
- login e-mail + hasło z V10; konto root według istniejącej konfiguracji
- nowa rejestracja wymaga e-maila, konto automatycznie otrzymuje rolę User
- po zalogowaniu oryginalna nawigacja/ekrany React na desktopie i telefonie
- `/account`: profil, uprawnienia, lista kont dla administratora oraz usunięcie konta
- `/radar`: odczyt prywatnych ogłoszeń z `user_search_offers_v9`
- `/searches`: lista i zapis pojedynczego radaru OLX (fraza, kategoria, budżet, aktywny/nieaktywny)
- `/notifications`: odczyt prywatnych alertów V8
- prywatność danych według `owner_id` i zabezpieczenie URL ofert
- zatrzymywanie innych modyfikacji w *podglądzie*; tam można się tylko logować i odczytywać dane

Jeszcze NIE zintegrowano z backendem V10:
- wieloplatformowego skanowania każdej frazy (V9 niezależnie pobiera OLX)
- wycen ROI/zysku na podstawie pełnego rynku (nie przedstawiamy fikcyjnych wycen)
- kompletnych operacji magazynu/flipów (oryginalny ekran może wyświetlać informację o braku API; oryginalne dane i narzędzia pozostają w `/centrum`)
- ręcznej analizy ofert, Vinted/Allegro Lokalnie/Otomoto i indywidualnej obserwacji
- opłacania i aktywacji pakietów w React (obsługa pozostaje w `/admin/uzytkownicy?legacy=1`)

**Nie publikuj V12 na produkcji, dopóki nie przejdziesz ścieżek `/account`, `/radar` i `/searches` w podglądzie LIVE.** Instalator domyślnie uruchamia osobny proces na 8094. Wdrożenie produkcyjne jest dostępne dopiero jako ręczny, odrębny etap.

## Wymagania

- Istniejący serwer `/opt/olx-bot` z Flask V10.1 / V11 oraz skanerem V9.
- Node.js 22+ i npm na Ubuntu (przeznaczone wyłącznie do kompilacji frontendu); internet do `npm ci`.
- Oryginalny ZIP: `/root/FlipRadar-Strona-i-Konta.zip`, SHA256 `6ff73ecbd418dbf0f38ae8c0a40a5c2e57e84fb2bdb779b2ce20a90c89d17591`. To ta sama paczka z rozmowy; instalator odrzuca inne źródła.
- Testy działają z Pythonem z `/opt/olx-bot/venv/bin/python`.

## Przygotowanie (NIE zmienia produkcji)

Prześlij tę niewielką paczkę `/root/FlipRadar_V12_ORIGINAL_REACT_LIVE_BRIDGE.zip` i wykonaj:

```bash
mkdir -p /opt/flipradar-v12
unzip -o /root/FlipRadar_V12_ORIGINAL_REACT_LIVE_BRIDGE.zip -d /opt/flipradar-v12
node --version
npm --version
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py prepare --zip /root/FlipRadar-Strona-i-Konta.zip
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py smoke
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py stage
```

`prepare` wykonuje `npm ci`, `npx expo export --platform web` i umieszcza **oryginalny** skompilowany React pod `/opt/flipradar-v12/dist`. Kompilacja może potrwać kilka minut.

`stage` uruchamia `flipradar-v12-preview.service` na `127.0.0.1:8094`. Nie restartuje serwera produkcyjnego 8089 i nie zmienia jego tras. Wersja na 8094 odczytuje bieżące konto i radary, lecz blokuje zapisy, usuwanie kont i edycję. Logowanie/wylogowanie na podglądzie jest dozwolone.

Na Windows:

```powershell
ssh -N -L 8094:127.0.0.1:8094 root@192.168.1.158
```

Otwórz `http://127.0.0.1:8094/login` i zaloguj się **na swoje istniejące konto testowe**. Test kont administratora wymaga tej samej konfiguracji `EnvironmentFile`, którą posiada jednostka `olx-dashboard-v2.service` — instalator kopiuje tylko ścieżki do plików środowiskowych, nie ich wartości.

Sprawdź `/bot`, `/radar`, `/searches`, `/account`. Dane są rzeczywiste; brak ofert oznacza brak wyników w bieżącej bazie. Skany i timery nadal działają tak jak wcześniej.

## Testy serwera

```bash
journalctl -u flipradar-v12-preview.service -n 50 --no-pager
curl -I http://127.0.0.1:8094/
curl -I http://127.0.0.1:8094/login
curl -I http://127.0.0.1:8094/account
systemctl is-active olx-dashboard-v2.service
```

Oczekuj `200`, `200`, `302` (bez zalogowania) i `active`.

## Publikacja — dopiero po teście, na wyraźną decyzję

```bash
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py publish
```

Publikacja zmienia wygląd ekranów konta, radaru i administratora, ale pozostawia `/` i działające skanery V9/V8 bez zmian. Instaluje adapter, robi kopię pliku overlay i kopię SQLite oraz restartuje tylko dashboard. Oryginalne specjalistyczne moduły V10 pozostają dostępne pod `/centrum` i `/admin/uzytkownicy?legacy=1`.

Awaryjne cofnięcie interfejsu (nie nadpisuje bazy):

```bash
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py rollback
```

## Dalsze prace

Po zatwierdzeniu UI dopisujemy adapter danych magazynu i pełną obsługę wycen, potem integracje pozostałych platform. Nie myl eksportu web-demo `web-demo/` z eksportem live; `web-demo/` jest wyłącznie demonstracją.
