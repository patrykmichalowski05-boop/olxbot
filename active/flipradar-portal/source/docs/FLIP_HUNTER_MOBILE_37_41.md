# Flip Hunter — podetapy techniczne 37-41

Cel: przygotowanie klienta Expo do nowego API.

## Status

- Mobilny kontrakt radaru: testowany offline
- Logowanie: ponownie wykorzystane z flip_core
- Reczna analiza: dostepna tylko po wlaczeniu flagi serwera
- Watchlista: API dodane do klienta Expo
- Fizyczny test iPhone: NIE
- Fizyczny test Android: NIE
- Publiczny serwer HTTPS: NIE
- Integracje marketplace: NIE

## Flaga aplikacji mobilnej

W mobile/.env:

EXPO_PUBLIC_FLIP_RADAR_SOURCE=universal

Domyslna wartosc: legacy.

Nowy tryb wymaga backendu:
universal_v2.mobile_bridge:create_app

i HTTPS oraz prawidlowego konta testowego.

Nie wpisuj do EXPO_PUBLIC haseł ani tokenow.

## Kryterium odbioru etapu glownego 5

Na iPhone i Android musimy osobno potwierdzic:
logowanie, radar, reczna analiza, watchlista,
kalkulator, odswiezanie tokenow i wylogowanie.

Samo przejscie unit testow NIE zalicza etapu 5.
