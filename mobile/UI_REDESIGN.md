# FlipRadar — desktop i mobile

Zmiany dotyczą wyłącznie `mobile/` na gałęzi `feature/flipradar-desktop-redesign`. Zachowano bazę integracji (`3df7447`) i dodany równolegle commit `stage 85 responsive dark sidebar` (`427766b`). Przebudowa jest zapisana w trzech kolejnych commitach na tej bazie.

## Audyt

- Domyślny motyw systemowy powodował jasny interfejs.
- Pionowy pasek zakładek był pozycjonowany absolutnie, bez rezerwacji miejsca na treść.
- Radar i pozostałe listy miały jedną rozciągniętą kolumnę.
- Nagłówki miały zbędny odstęp po lewej i niespójny układ działań.
- Brakowało dashboardu oraz konfiguracji ESLint 9.
- Wynik synchronicznej analizy LIVE był pomijany. Formularze kosztów i sprzedaży znajdowały się pod otwartym oknem potwierdzenia.

## Układ

| Szerokość | Nawigacja | Radar |
| --- | --- | --- |
| 1920 i 1440 px | Sidebar 250 px, pasek wyszukiwania | 3 kolumny lub tabela |
| 1024 px | Sidebar 250 px | 2 kolumny lub przewijana tabela |
| 768–1023 px | Kompaktowy sidebar 80 px | 2 kolumny lub przewijana tabela |
| Poniżej 768 px | Dolna nawigacja, 6 zakładek | 1 kolumna |

Ciemny motyw jest domyślny; zapisane preferencje oraz wybór jasnego i systemowego motywu pozostają dostępne. Sidebar obejmuje również ekrany szczegółów, analitykę i powiadomienia. Breakpointy zachowują zgodność pierwszego renderu SSR z hydratacją Expo Web.

## Dane i operacje

- Dashboard pobiera pierwszą stronę radaru, flipów i powiadomień przez istniejący klient API. Zakres każdej statystyki jest opisany w interfejsie.
- Brak statusu aktywności, brak wyceny lub brak wyniku finansowego oznacza „Brak danych” / „Brak wyceny”. Nie ma zastępowania nieznanych wartości zerem ani odtwarzania zysku z cen.
- Analityka sumuje kwoty zwrócone przez backend. Wykres pokazuje wyniki sprzedanych przedmiotów, bez wymyślonej osi czasu sprzedaży. Sumy różnych walut nie są łączone.
- Zapis finansowy LIVE przyjmuje wyłącznie UUID. Liczbowy identyfikator legacy nie jest przekazywany jako identyfikator PostgreSQL. Bez powiązania oferty z rejestrem flipów formularz zakupu pozostaje dostępny do podglądu, ale zapis jest zablokowany.
- Historia obserwowanego produktu jest pobierana tylko dla jawnego klucza `listing:<liczbowe_id>` przez istniejący endpoint szczegółów i historii. Dla innych kluczy braki są oznaczone.
- Zachowano filtry, profile, paginację radaru i powiadomień, obserwowanie, ponowną analizę, zakup, koszty, sprzedaż, potwierdzenia i klucze idempotencji. DEMO nie wykonuje żądań do API LIVE.
- Kontrakty API v1/v2, funkcje kalkulacji finansowych i kod backendu nie zostały zmienione. Nie wykonywano wdrożenia ani operacji na usługach produkcyjnych.

## Walidacja

Po każdym etapie wykonano `npm run typecheck`, `npm test -- --runInBand` oraz `npm run lint`. Końcowy zestaw: 7 zestawów, 21 testów; lint bez błędów i ostrzeżeń.

Eksport Expo Web zweryfikowano w Chromium przy szerokościach 1920, 1440, 1024, 1023, 820, 768, 767, 390 i 320 px. Sprawdzono liczbę kolumn, szerokość sidebaru, brak poziomego przepełnienia, dolną nawigację i błędy JavaScript.

Scenariusze DEMO: logowanie, dashboard, siatka/tabela, filtry i zapis profilu, obserwowanie/usuwanie, wybór kategorii i wynik AI, formularze kosztów/sprzedaży w oknie potwierdzenia, analityka, skrzynka, motywy, diagnostyka połączenia i wylogowanie.

Tryb LIVE sprawdzono na izolowanych odpowiedziach testowych: brak wyceny/statusu/zrealizowanego wyniku, HTTP 503, synchroniczny wynik AI, zachowanie konkretnego adresu po logowaniu i blokada zapisu finansowego dla ID legacy. Test nie wykonywał operacji finansowych na prawdziwym API.

Eksporty Hermes dla iOS i Androida zostały zbudowane. Nie przeprowadzono uruchomienia na fizycznych telefonach ani w symulatorze natywnym; kontrola mobilnego wyglądu obejmowała Expo Web.

## Uruchomienie w dev

```bash
cd mobile
npm ci
npm run typecheck
npm test -- --runInBand
npm run lint
npx expo start --clear
```

Po zmianie `EXPO_PUBLIC_*`, w tym DEMO/LIVE lub adresu API, wyczyść cache Metro (`--clear`). Przy eksporcie: `npx expo export --clear --platform web`. Są to wartości wbudowywane w bundle; stary cache może zachować poprzednią konfigurację.

Kod, historia commitów i potwierdzone wyniki walidacji są przygotowane do przeniesienia do repozytorium developerskiego.
