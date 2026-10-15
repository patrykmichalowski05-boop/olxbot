# FlipRadar — przebudowa UI mobile

Bazowa gałąź: `feature/flipradar-watch-review`, commit `b72d2d1bcb7302e19d3bec08ab67ff12a71fa513`.
Nowa gałąź: `feature/flipradar-mobile-premium`.

## Zakres

- Expo, React Native, Expo Router i TypeScript pozostają bez zmian wersji.
- Wszystkie zmiany mieszczą się w `mobile/`.
- Backend, adresy i metody endpointów, formaty żądań, tokeny, obsługa sesji oraz konfiguracja połączenia pozostają bez zmian.
- Zmiany w `api/errors.ts` dotyczą wyłącznie tłumaczenia błędów na tekst dla użytkownika. Mapper odczytuje opcjonalne `ai_summary` i `image_url` z istniejącego pola `valuation`.

## Interfejs

- Motyw: ciemny granat, akcent cyan, semantyczne kolory, ujednolicone odstępy, typografia i zaokrąglenia. Nowe instalacje startują w ciemnym motywie; zapisane preferencje oraz wybór jasnego/systemowego motywu działają dalej.
- Radar: zwarty nagłówek, statystyki, wyszukiwarka z opóźnieniem 300 ms, przewijane kategorie i arkusz filtrów z sortowaniem. Zachowane filtrowanie po cenie, wyniku, ROI i platformie, zapisywanie profili oraz stronicowanie.
- Karty: miniatura po lewej, platforma, dwuwierszowy tytuł, cena zakupu i prognoza odsprzedaży, wyróżniony potencjalny wynik, ROI, decyzja, ryzyko, tekst z analizy, szczegóły i zapis/usuń zapis. Brak zdjęcia lub błąd pobierania obrazu pokazuje ikonę kategorii.
- Dolny pasek: Radar, Zapisane, Analiza, Flipy, Konto. Akcent aktywnej zakładki, bez obciętych etykiet i z uwzględnieniem bezpiecznej strefy urządzenia. Na urządzeniach mobilnych znika po otwarciu klawiatury.
- Zapisane: nowe karty, stan pusty z przejściem do radaru, czytelne błędy pobierania i usuwania, ponawianie operacji oraz zachowanie ostatnio pobranych danych przy błędzie odświeżenia.
- Analiza: wybór kategorii, nowe pola i walidacja ceny, objaśnienie działania, CTA oraz stany analizy. Odczytywany jest zarówno wynik zwracany od razu, jak i wynik zadania odpytywanego przez istniejący klient API.
- Flipy: przegląd kapitału i zrealizowanego wyniku, statusy transakcji, odświeżone karty i analityka. Bez skonfigurowanej przestrzeni transakcji wyświetlany jest pusty stan „Nie masz jeszcze zapisanych flipów” i CTA, bez nazw zmiennych konfiguracyjnych.
- Wspólne stany: skeletony respektujące ograniczenie animacji, puste listy z ikoną i akcją, przyjazne błędy z ponowieniem. W webie chronione zakładki czekają z renderowaniem na gotowość istniejącej sesji, aby zachować zgodność z HTML generowanym statycznie.

## Znaczenie danych

Statystyki radaru obejmują załadowane oferty po aktualnych filtrach. Nie są sumą całego rynku. Kolejne strony aktualizują podsumowanie.

- Średni ROI uwzględnia wyłącznie dostępne, skończone wartości ofert z wyceną.
- Hot deal oznacza kandydata BUY/BUY_CANDIDATE z wiarygodną wyceną i dodatnim potencjalnym wynikiem.
- Potencjalny zysk to suma dodatnich prognoz. Brak wyceny nie jest przedstawiany jako zysk równy zero.
- Badge BUY/WATCH/SKIP skraca prezentację decyzji; oryginalna decyzja pozostaje w danych i dostępnej etykiecie.
- Brak informacji o ryzyku nie oznacza niskiego ryzyka.
- Etykieta „Insight AI” pojawia się tylko dla istniejącego podsumowania `ai_summary`. Tekst zastępczy ma etykietę „Sygnał z analizy”.
- Portfel i analityka opisują pobrane transakcje (do 30), bez wykresów z fikcyjnymi danymi.

## Walidacja

Polecenia w `mobile/`:

```sh
npm run typecheck
npm test -- --runInBand
npx expo export --platform all --clear
```

`npm run typecheck` przechodzi. Wszystkie 29 testów jednostkowych w 7 zestawach przechodzi.

Wykonano testy interfejsu w Chromium dla szerokości 320, 390, 768 i 1280 px. Sprawdzono nawigację, filtry, zapisywanie i usuwanie ofert, puste stany, formularz, wybór motywu oraz ponawianie po błędach usługi.

W trybie live przeszły 42 kontrole UI i kontraktów żądań, bez błędów wykonania Reacta, w tym ponowne logowanie po odświeżeniu chronionego ekranu.

Testy trybu live używają kontrolowanych odpowiedzi HTTP i sprawdzają istniejące ścieżki oraz treść żądań. Nie wykonują operacji na produkcyjnym koncie. Eksport iOS/Android sprawdza budowanie pakietów, nie zastępuje testu na fizycznych urządzeniach.

## Pliki zmienione i dodane

- `mobile/UI_REDESIGN.md`
- `mobile/src/api/demo/fixtures.ts`
- `mobile/src/api/errors.ts`
- `mobile/src/api/mappers/opportunity.ts`
- `mobile/src/app/(auth)/login.tsx`
- `mobile/src/app/(tabs)/_layout.tsx`
- `mobile/src/app/(tabs)/analyze/index.tsx`
- `mobile/src/app/(tabs)/flips/index.tsx`
- `mobile/src/app/(tabs)/radar/index.tsx`
- `mobile/src/app/(tabs)/settings/index.tsx`
- `mobile/src/app/(tabs)/watched/index.tsx`
- `mobile/src/app/analytics/index.tsx`
- `mobile/src/components/AppScreen.tsx`
- `mobile/src/components/Badge.tsx`
- `mobile/src/components/DecisionBadge.tsx`
- `mobile/src/components/DemoBanner.tsx`
- `mobile/src/components/EmptyState.tsx`
- `mobile/src/components/ErrorState.tsx`
- `mobile/src/components/FilterSheet.tsx`
- `mobile/src/components/FormField.tsx`
- `mobile/src/components/Header.tsx`
- `mobile/src/components/IconButton.tsx`
- `mobile/src/components/LoadingSkeleton.tsx`
- `mobile/src/components/PremiumTabBar.tsx`
- `mobile/src/components/PrimaryButton.tsx`
- `mobile/src/components/ProductCard.tsx`
- `mobile/src/components/StatCard.tsx`
- `mobile/src/features/opportunity/presentation.ts`
- `mobile/src/features/opportunity/types.ts`
- `mobile/src/hooks/useDebouncedValue.ts`
- `mobile/src/test/radar-presentation.test.ts`
- `mobile/src/test/user-errors.test.ts`
- `mobile/src/theme/ThemeProvider.tsx`
- `mobile/src/theme/tokens.ts`
- `mobile/src/utils/labels.ts`
