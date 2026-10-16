# Flip Hunter - test na telefonie

## 1. Backend

Aplikacja wymaga zaufanego adresu HTTPS.

Nie kieruj publicznego ruchu bezposrednio na
serwer developerski Uvicorn.

Przed testami upewnij sie, ze backend zostal
zabezpieczony reverse proxy HTTPS i dostepem
ograniczonym do uprawnionych uzytkownikow.

## 2. Adres API

W katalogu mobile:

```bash
bash scripts/set_api_url.sh https://api.twojadomena.pl
```

Adres jest przykladowy. Uzyj rzeczywistego
adresu API.

Skrypt sprawdzi TLS i endpoint /api/v1/me.
Dopiero potem zapisze plik .env.

W .env nie umieszczaj tokenow, hasel,
sekretow serwera ani kluczy AI.

## 3. Expo

```bash
cd mobile
npm ci
bash scripts/start_expo.sh
```

W przypadku wymagan dodatkowych Expo Tunnel
wykonaj polecenia wyswietlone przez Expo.

Zainstaluj zgodna z projektem wersje Expo Go
na urzadzeniu, jesli jest dostepna.

Alternatywnie przygotuj development build.
Samo sprawdzenie TypeScript nie gwarantuje
zgodnosci z Expo Go.

## 4. Test reczny

1. Otworz projekt na telefonie.
2. Sprawdz polaczenie z API.
3. Zaloguj sie kontem testowym.
4. Otworz radar.
5. Wyszukaj RTX lub Ryzen.
6. Zmien filtry.
7. Otworz szczegoly oferty.
8. Przejdz do kalkulatora.
9. Sprawdz zysk i ROI.
10. Wyloguj sie.
11. Sprawdz, czy sesja nie pozwala
    na odczyt radaru po wylogowaniu.

## 5. Uwaga

Uzycie tunelu Expo udostepnia serwer
developerski Metro do testow. Nie traktuj
go jak produkcyjnego hostingu aplikacji.

Test na telefonie musi zostac potwierdzony
osobno. Samo uruchomienie Expo nie jest
dowodem dzialania aplikacji i API.
