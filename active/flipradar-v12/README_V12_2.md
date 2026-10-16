# FlipRadar V12.2 — publikacja ORYGINALNEGO React z podglądu 8094

Ta poprawka jest dla serwera, na którym **V12.1 `resume` / `smoke` / `stage` już się udały** i panel React jest dostępny pod `127.0.0.1:8094` (tak jak w potwierdzonych logach). Nie wymaga `npm ci`, rekompilacji Expo ani ponownego wgrywania oryginalnego ZIP-a.

## Co zmienia w produkcji

- `/` → **identyczny skompilowany `dist/index.html`** z zaakceptowanego podglądu V12 na 8094 (V11 używał osobnego HTML).
- `/login`, `/register`, `/rejestracja` → oryginalne ekrany React z istniejącym uwierzytelnianiem V10.
- `/bot`, `/radar`, `/searches`, `/account`, `/notifications` → oryginalne chronione ekrany React (część operacji wciąż może zwracać 501, gdy backend nie ma jeszcze adaptera).
- `/admin/uzytkownicy` → oryginalny ekran kont React; wersja administracyjna V10 dostępna przez `/admin/uzytkownicy?legacy=1`.
- `/dev/flip-hunter`, skanery V8/V9 i specjalistyczne trasy zachowują istniejące uprawnienia.
- Cloudflare Access i jego ustawienia **nie są modyfikowane**. Aby oglądać domenę z zewnątrz, nadal należy przejść dotychczasową autoryzację Access.

## Instalacja na Ubuntu

Skopiuj **`FlipRadar_V12_2_PUBLISH_ORIGINAL_UI.zip`** do `/root/` (WinSCP).

```bash
unzip -o /root/FlipRadar_V12_2_PUBLISH_ORIGINAL_UI.zip -d /opt/flipradar-v12
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/tests/test_deploy_v12_2.py
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py smoke
```

**Jeśli oba testy skończą się PASS**, publikuj:

```bash
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py publish
```

Publikator najpierw testuje obecnego Flaska i trasę `/` **w osobnym procesie, z jednorazowymi danymi konta i pustą tymczasową SQLite**. Następnie wykonuje backup produkcyjnego overlay oraz spójny backup SQLite (bazy nie przywraca automatycznie, by nie usuwać nowych rejestracji), instaluje most V12 i restartuje wyłącznie `olx-dashboard-v2.service`. Sprawdza HTTP 200 dla React i API, 302 dla chronionych ekranów, skrypt JS React. Gdy test nie przechodzi, cofa kod i restartuje poprzedni dashboard.

## Kontrola na serwerze

```bash
systemctl is-active olx-dashboard-v2.service
curl -sS -o /dev/null -w 'HOME: %{http_code}\n' http://127.0.0.1:8089/
curl -sS -o /dev/null -w 'LOGIN: %{http_code}\n' http://127.0.0.1:8089/login
curl -sS -o /dev/null -w 'ADMIN ANON: %{http_code}\n' http://127.0.0.1:8089/admin/uzytkownicy
curl -sS -o /dev/null -w 'API: %{http_code}\n' http://127.0.0.1:8089/api/v1/public/config
curl -sS -o /dev/null -w 'REACT ASSETS: %{http_code}\n' "http://127.0.0.1:8089/$(find /opt/flipradar-v12/dist/_expo/static/js/web/ -name '*.js' -printf '_expo/static/js/web/%f\n' -quit)"
```

Oczekiwane: `active`, HOME 200, LOGIN 200, ADMIN ANON 302, API 200, REACT ASSETS 200.

### Potwierdzenie oryginalnego HTML, bajt po bajcie

```bash
curl -fsS http://127.0.0.1:8089/ | sha256sum
sha256sum /opt/flipradar-v12/dist/index.html
```

Skróty muszą się zgadzać. Możesz również porównać z podglądem `curl -fsS http://127.0.0.1:8094/ | sha256sum`.

## Cofnięcie interfejsu

```bash
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py rollback
```

Przywraca plik overlay poprzedniej strony. Nie nadpisuje bazy, nie zmienia Cloudflare ani timerów. Kopia jest w `/opt/olx-bot-budget-dev/v12_backups`.

## Ograniczenia

To **publikacja oryginalnego wyglądu i dostępnych adapterów**, a nie ukończenie funkcjonalności każdego przycisku. Wciąż brak pełnych operacji magazynu/finansów, wielu platform i płatności w React; dla niezaimplementowanych funkcji API odpowiada błędem zamiast udawać sukces. Nie wolno przedstawiać tego jako kompletnego produktu SaaS.
