# FlipRadar V12.1 — naprawa przerwanego prepare i smoke

Ta paczka zawiera **tylko poprawiony instalator** `deploy_v12.py` i niezależny test regresji. Nie zawiera frontendu React, nie aktualizuje kont, nie zmienia SQLite ani produkcyjnej usługi.

## Naprawione problemy

1. Przy instalacji do `/opt/flipradar-v12` skrypt próbował kopiować `v12_bridge.py` na ten sam plik, powodując `shutil.SameFileError`.
2. Test `smoke` uruchamiany z `/opt/flipradar-v12/v12_smoke.py` nie znał ścieżki do `multiuser_v2.py`. Dodałem odpowiedni `PYTHONPATH` **wyłącznie w procesie testowym**.
3. Kompilacja `npm ci` i `expo export` ukończyła się przed błędem, więc wprowadzono akcję **`resume`**: dokańcza przygotowanie z `/opt/flipradar-v12/mobile/dist`, bez ponownego npm.

## Uruchomienie

Prześlij `FlipRadar_V12_1_FIX.zip` do `/root/`, następnie:

```bash
unzip -o /root/FlipRadar_V12_1_FIX.zip -d /opt/flipradar-v12
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/tests/test_v12_1.py
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py resume --zip /root/FlipRadar-Strona-i-Konta.zip
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py smoke
```

**Dopiero po PASS**:

```bash
/opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py stage
systemctl status flipradar-v12-preview.service --no-pager -n 12
curl -I http://127.0.0.1:8094/
curl -I http://127.0.0.1:8094/login
curl -I http://127.0.0.1:8094/account
```

Oczekiwane: 200 dla `/` i `/login`, 302 dla `/account` bez sesji.

Na Windows można oglądać podgląd przez tunel SSH:

```powershell
ssh -N -L 8094:127.0.0.1:8094 root@192.168.1.158
```

Podgląd `http://127.0.0.1:8094/` używa prawdziwej sesji kont, ale **blokuje modyfikacje danych**. Wciąż **nie** uruchamiaj `publish`, dopóki nie obejrzysz panelu i nie sprawdzisz działania.

W razie błędu `smoke` lub `stage` podaj pełny traceback oraz `journalctl -u flipradar-v12-preview.service -n 40 --no-pager`. Nie powtarzaj `prepare` — wykonany `expo export` pozostaje na dysku.
